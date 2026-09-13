import express from "express";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export interface DiseaseRecord {
  disease_id: string;
  crop: string;
  disease_name: string;
  pathogen_type: string;
  symptoms: string;
  favorable_conditions: string;
  low_risk_advisory: string;
  medium_risk_advisory: string;
  high_risk_advisory: string;
  expert_advisory: string;
  preventive_measures: string;
  organic_treatment: string;
  chemical_treatment: string;
}

// Load disease database from JSON
let diseasesData: DiseaseRecord[] = [];
try {
  const jsonPath = path.join(__dirname, "src", "diseases_data.json");
  if (fs.existsSync(jsonPath)) {
    diseasesData = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
  }
} catch (err) {
  console.error("Failed to load diseases_data.json:", err);
}

// Lazy initialization for Gemini client
let geminiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI | null {
  if (!process.env.GEMINI_API_KEY) {
    return null;
  }
  if (!geminiClient) {
    geminiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  }
  return geminiClient;
}

// Microclimate risk evaluation helper
function computeMicroclimateRisk(
  humidity: number,
  temp: number,
  rainfall: number,
  favorableConditions: string,
  sustainedHighHumidityHours: number = 0
): { score: number; details: string } {
  // Humidity score: 50% is baseline; >= 80% is high risk
  const humidityScore = Math.min(1.0, Math.max(0.0, (humidity - 45) / 45));
  
  // Sustained moisture factor (if hours >= 80% RH over last 24-48h)
  const sustainedFactor = Math.min(0.2, (sustainedHighHumidityHours / 48) * 0.25);

  // Temperature fit based on favorable conditions text
  let tempScore = 0.5;
  const favLower = favorableConditions.toLowerCase();
  
  if (favLower.includes("cool") || favLower.includes("15-20") || favLower.includes("15-25")) {
    tempScore = (temp >= 14 && temp <= 24) ? 0.9 : 0.35;
  } else if (favLower.includes("warm") || favLower.includes("24-29") || favLower.includes("25-30") || favLower.includes("25-28")) {
    tempScore = (temp >= 22 && temp <= 32) ? 0.95 : 0.4;
  } else if (favLower.includes("high temperature") || favLower.includes("hot")) {
    tempScore = (temp >= 30) ? 0.9 : 0.45;
  } else {
    tempScore = (temp >= 18 && temp <= 32) ? 0.75 : 0.4;
  }

  // Rainfall / leaf wetness score
  const rainScore = Math.min(1.0, Math.max(0.0, rainfall / 15.0));

  // Weighted composite: 45% Humidity (+ sustained), 35% Temp match, 20% Leaf wetness/rain
  const raw = (0.45 * Math.min(1.0, humidityScore + sustainedFactor)) + (0.35 * tempScore) + (0.20 * rainScore);
  const score = Math.round(Math.min(1.0, Math.max(0.05, raw)) * 1000) / 1000;

  const details = `Humidity ${humidity}% (${Math.round(humidityScore * 100)}% risk contribution), Temp ${temp}°C vs pattern "${favorableConditions}" (${Math.round(tempScore * 100)}% fit), Rain ${rainfall}mm (${Math.round(rainScore * 100)}% wetness factor). Sustained dampness: ${sustainedHighHumidityHours} hrs.`;

  return { score, details };
}

// Weather fetching helper using free reliable Open-Meteo API
async function fetchLiveWeather(lat: number, lon: number): Promise<{
  temperature: number;
  humidity: number;
  rainfall: number;
  windSpeed: number;
  weatherCode: number;
  weatherDescription: string;
  sustainedHighHumidityHours: number;
  source: string;
}> {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&hourly=relative_humidity_2m,temperature_2m,precipitation&forecast_days=2&timezone=auto`;
    const resp = await fetch(url, { signal: AbortSignal.timeout(6000) });
    if (!resp.ok) {
      throw new Error(`Open-Meteo returned status ${resp.status}`);
    }
    const data = await resp.json();

    const current = data.current || {};
    const hourly = data.hourly || {};
    const humidities: number[] = hourly.relative_humidity_2m || [];

    // Count how many hours relative humidity was >= 80%
    const sustainedHours = humidities.slice(0, 48).filter((h: number) => h >= 80).length;

    const weatherCode = current.weather_code ?? 0;
    const weatherDescMap: Record<number, string> = {
      0: "Clear sky",
      1: "Mainly clear",
      2: "Partly cloudy",
      3: "Overcast",
      45: "Foggy",
      48: "Depositing rime fog",
      51: "Light drizzle",
      53: "Moderate drizzle",
      55: "Dense drizzle",
      61: "Slight rain",
      63: "Moderate rain",
      65: "Heavy rain",
      80: "Slight rain showers",
      81: "Moderate rain showers",
      82: "Violent rain showers",
      95: "Thunderstorm",
      96: "Thunderstorm with slight hail",
    };

    return {
      temperature: current.temperature_2m ?? 26.5,
      humidity: current.relative_humidity_2m ?? 78,
      rainfall: current.precipitation ?? (current.rain ?? 0),
      windSpeed: current.wind_speed_10m ?? 8.2,
      weatherCode,
      weatherDescription: weatherDescMap[weatherCode] || "Cloudy / Humid",
      sustainedHighHumidityHours: sustainedHours,
      source: "Open-Meteo Real-Time Meteorological API",
    };
  } catch (err: any) {
    console.warn("Live weather fetch failed, using realistic regional default:", err.message);
    return {
      temperature: 26.8,
      humidity: 82,
      rainfall: 8.5,
      windSpeed: 10.5,
      weatherCode: 3,
      weatherDescription: "Humid overcast with intermittent showers (regional estimate)",
      sustainedHighHumidityHours: 28,
      source: "Estimated Microclimate Fallback",
    };
  }
}

// Generate farmer-friendly explanation
async function generateFarmerExplanation(
  record: DiseaseRecord,
  riskLevel: string,
  finalScore: number,
  weatherInfo: { temp: number; humidity: number; rain: number; sustainedHours: number },
  language: string = "English"
): Promise<{ text: string; source: "gemini" | "deterministic" }> {
  const levelAdvice =
    riskLevel === "HIGH"
      ? record.high_risk_advisory
      : riskLevel === "MEDIUM"
      ? record.medium_risk_advisory
      : record.low_risk_advisory;

  const gemini = getGeminiClient();
  if (gemini) {
    try {
      const prompt = `You are a respectful, knowledgeable Krishi Vigyan Kendra (KVK) agricultural extension specialist writing directly to an Indian farmer.
LANGUAGE REQUESTED: ${language}

CRITICAL ANTI-HALLUCINATION CONSTRAINTS:
1. ONLY rephrase and communicate the verified database facts provided below.
2. DO NOT invent or recommend any chemical names, brand names, dosages, or treatments that are NOT explicitly listed below.
3. Keep the tone empathetic, practical, and clear.
4. Explain clearly how the current weather (${weatherInfo.temp}°C, ${weatherInfo.humidity}% humidity, ${weatherInfo.rain}mm rain) creates risk for ${record.disease_name} in ${record.crop}.

VERIFIED FACTS TO USE:
- Crop: ${record.crop}
- Disease: ${record.disease_name} (Pathogen: ${record.pathogen_type})
- Symptoms: ${record.symptoms}
- Favorable Weather: ${record.favorable_conditions}
- Current Computed Risk: ${riskLevel} (Composite Score: ${finalScore})
- Action Advice: ${levelAdvice}
- Preventive Measures: ${record.preventive_measures}
- Organic Remedy: ${record.organic_treatment}
- Chemical Remedy: ${record.chemical_treatment}
- Scientific / Expert Note: ${record.expert_advisory}

FORMAT YOUR RESPONSE:
1. Warm greeting to the farmer (e.g. "Namaste Kisan Bhai / Farmer Ji")
2. Simple explanation of current field risk & weather trigger
3. Visible symptoms to inspect today
4. Immediate step-by-step action (Preventive, Organic, Chemical) strictly matching the facts above
5. Expert recommendation`;

      // Call Gemini 3.8 Flash (per current @google/genai guidelines)
      const modelsToTry = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-flash-latest"];
      let textResult = "";

      for (const modelName of modelsToTry) {
        try {
          const res = await gemini.models.generateContent({
            model: modelName,
            contents: prompt,
          });
          if (res.text) {
            textResult = res.text.trim();
            break;
          }
        } catch (mErr: any) {
          console.warn(`Model ${modelName} call failed, trying next fallback:`, mErr?.message || mErr);
        }
      }

      if (textResult) {
        return { text: textResult, source: "gemini" };
      }
    } catch (llmErr) {
      console.warn("Gemini generation failed, using deterministic fallback:", llmErr);
    }
  }

  // Multilingual deterministic fallback templates
  let text = "";
  if (language === "Hindi") {
    text = `नमस्ते किसान भाई!

हमने आपके ${record.crop} खेत का निरीक्षण और मौसम मूल्यांकन किया है। वर्तमान में क्षेत्र का तापमान ${weatherInfo.temp}°C, सापेक्ष आर्द्रता ${weatherInfo.humidity}%, और वर्षा ${weatherInfo.rain} मिमी दर्ज की गई है। यह मौसम ${record.disease_name} के संक्रमण के अनुकूल परिस्थितियों (${record.favorable_conditions}) से मेल खाता है।

🔍 आज जांचे जाने वाले प्रमुख लक्षण:
${record.symptoms}

⚠️ वर्तमान जोखिम स्तर: ${riskLevel === "HIGH" ? "उच्च (HIGH)" : riskLevel === "MEDIUM" ? "मध्यम (MEDIUM)" : "निम्न (LOW)"} जोखिम (समग्र स्कोर: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 रोग से बचाव के निवारक उपाय:
${record.preventive_measures}

🛡️ कृषि विज्ञान केंद्र (KVK) द्वारा सत्यापित उपचार:
• जैविक उपचार: ${record.organic_treatment}
• रासायनिक उपचार: ${record.chemical_treatment}

💡 वैज्ञानिक एवं विशेषज्ञ सलाह:
${record.expert_advisory}`;
  } else if (language === "Punjabi") {
    text = `ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਕਿਸਾਨ ਵੀਰ ਜੀ!

ਅਸੀਂ ਤੁਹਾਡੇ ${record.crop} ਦੇ ਖੇਤ ਦਾ ਮੌਸਮ ਅਤੇ ਬਿਮਾਰੀ ਜੋਖਮ ਮੁਲਾਂਕਣ ਕੀਤਾ ਹੈ। ਇਸ ਵੇਲੇ ਤਾਪਮਾਨ ${weatherInfo.temp}°C, ਨਮੀ ${weatherInfo.humidity}%, ਅਤੇ ਬਾਰਿਸ਼ ${weatherInfo.rain} ਮਿਲੀਮੀਟਰ ਹੈ। ਇਹ ਮੌਸਮ ${record.disease_name} ਦੇ ਫੈਲਾਅ ਲਈ ਅਨੁਕੂਲ ਹਾਲਤਾਂ (${record.favorable_conditions}) ਨਾਲ ਮੇਲ ਖਾਂਦਾ ਹੈ।

🔍 ਅੱਜ ਖੇਤ ਵਿੱਚ ਵੇਖਣਯੋਗ ਲੱਛਣ:
${record.symptoms}

⚠️ ਮੌਜੂਦਾ ਜੋਖਮ ਮੁਲਾਂਕਣ: ${riskLevel === "HIGH" ? "ਉੱਚ (HIGH)" : riskLevel === "MEDIUM" ? "ਦਰਮਿਆਨਾ (MEDIUM)" : "ਘੱਟ (LOW)"} ਜੋਖਮ (ਕੁੱਲ ਸਕੋਰ: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 ਬਚਾਅ ਅਤੇ ਸਫ਼ਾਈ ਦੇ ਉਪਾਅ:
${record.preventive_measures}

🛡️ ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ (KVK) ਦੁਆਰਾ ਪ੍ਰਮਾਣਿਤ ਇਲਾਜ:
• ਜੈਵਿਕ ਇਲਾਜ: ${record.organic_treatment}
• ਰਸਾਇਣਕ ਇਲਾਜ: ${record.chemical_treatment}

💡 ਮਾਹਿਰਾਂ ਦੀ ਸਲਾਹ:
${record.expert_advisory}`;
  } else if (language === "Bengali") {
    text = `নমস্কার কৃষক ভাই!

আমরা আপনার ${record.crop} ফসলের ক্ষেত এবং আবহাওয়া পর্যবেক্ষণ করেছি। বর্তমানে ক্ষেতের তাপমাত্রা ${weatherInfo.temp}°C, আর্দ্রতা ${weatherInfo.humidity}%, এবং বৃষ্টিপাত ${weatherInfo.rain} মিমি। এই আবহাওয়া ${record.disease_name} রোগের অনুকূল পরিস্থিতি (${record.favorable_conditions}) তৈরি করেছে।

🔍 আজই পরীক্ষা করার মতো লক্ষণ:
${record.symptoms}

⚠️ বর্তমান ঝুঁকি স্তর: ${riskLevel === "HIGH" ? "উচ্চ (HIGH)" : riskLevel === "MEDIUM" ? "মাঝারি (MEDIUM)" : "কম (LOW)"} ঝুঁকি (মোট স্কোর: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 প্রতিরোধমূলক ব্যবস্থা:
${record.preventive_measures}

🛡️ কৃষি বিজ্ঞান কেন্দ্র অনুমোদিত চিকিৎসা:
• জৈব চিকিৎসা: ${record.organic_treatment}
• রাসায়নিক চিকিৎসা: ${record.chemical_treatment}

💡 বিশেষজ্ঞ পরামর্শ:
${record.expert_advisory}`;
  } else if (language === "Marathi") {
    text = `रामराम शेतकरी बंधूंनो!

आम्ही आपल्या ${record.crop} पिकाचे आणि स्थानिक हवामानाचे विश्लेषण केले आहे. सध्याचे तापमान ${weatherInfo.temp}°C, हवेतील आर्द्रता ${weatherInfo.humidity}%, आणि पाऊस ${weatherInfo.rain} मिमी आहे. हे वातावरण ${record.disease_name} रोगाच्या प्रसारास अनुकूल (${record.favorable_conditions}) आहे.

🔍 आज पिकावर तपासण्याची लक्षणे:
${record.symptoms}

⚠️ सध्याची रोग जोखीम: ${riskLevel === "HIGH" ? "उच्च (HIGH)" : riskLevel === "MEDIUM" ? "मध्यम (MEDIUM)" : "कमी (LOW)"} जोखीम (एकूण गुण: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 प्रतिबंधात्मक उपाययोजना:
${record.preventive_measures}

🛡️ कृषी विज्ञान केंद्र प्रमाणित उपाय:
• सेंद्रिय उपचार: ${record.organic_treatment}
• रासायनिक फवारणी: ${record.chemical_treatment}

💡 तज्ज्ञ सल्ला:
${record.expert_advisory}`;
  } else if (language === "Telugu") {
    text = `నమస్కారం రైతు సోదరులారా!

మీ ${record.crop} పంట పొలాన్ని మరియు స్థానిక వాతావరణ పరిస్థితులను పరిశీలించాము. ప్రస్తుతం ఉష్ణోగ్రత ${weatherInfo.temp}°C, తేమ ${weatherInfo.humidity}%, వర్షపాతం ${weatherInfo.rain} మి.మీ. గా నమోదైంది. ఈ వాతావరణం ${record.disease_name} వ్యాప్తికి అనుకూల పరిస్థితులకు (${record.favorable_conditions}) దగ్గరగా ఉంది.

🔍 నేడు గమనించాల్సిన లక్షణాలు:
${record.symptoms}

⚠️ ప్రస్తుత వ్యాధి తీవ్రత: ${riskLevel === "HIGH" ? "అధిక (HIGH)" : riskLevel === "MEDIUM" ? "మధ్యస్థ (MEDIUM)" : "తక్కువ (LOW)"} రిస్క్ (మొత్తం స్కోర్: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 నివారణ చర్యలు:
${record.preventive_measures}

🛡️ కృషి విజ్ఞాన కేంద్రం (KVK) సిఫార్సు చేసిన యాజమాన్య పద్ధతులు:
• సేంద్రీయ నివారణ: ${record.organic_treatment}
• రసాయన నివారణ: ${record.chemical_treatment}

💡 శాస్త్రవేత్తల మరియు నిపుణుల సలహా:
${record.expert_advisory}`;
  } else {
    // English default
    text = `Namaste Farmer Ji!

We have evaluated your ${record.crop} field. Right now, the ambient conditions show a temperature of ${weatherInfo.temp}°C with ${weatherInfo.humidity}% relative humidity and ${weatherInfo.rain} mm rainfall. These conditions closely match the favorable pattern for ${record.disease_name} (${record.favorable_conditions}).

🔍 SYMPTOMS TO INSPECT:
${record.symptoms}

⚠️ CURRENT RISK ASSESSMENT: ${riskLevel} RISK (Overall Score: ${finalScore.toFixed(2)} / 1.00)
${levelAdvice}

🌱 PREVENTIVE SANITATION:
${record.preventive_measures}

🛡️ VERIFIED TREATMENT ACTIONS:
• Organic: ${record.organic_treatment}
• Chemical: ${record.chemical_treatment}

💡 EXPERT GUIDANCE:
${record.expert_advisory}`;
  }

  return { text, source: "deterministic" };
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API Route: Health check
  app.get("/api/health", (req, res) => {
    res.json({
      status: "healthy",
      service: "Crop Disease Risk Advisory System (SIH 2026)",
      total_diseases: diseasesData.length,
      supported_crops: Array.from(new Set(diseasesData.map(d => d.crop))).sort(),
      gemini_configured: Boolean(process.env.GEMINI_API_KEY),
      openweather_configured: Boolean(process.env.OPENWEATHER_API_KEY),
      timestamp: new Date().toISOString(),
    });
  });

  // API Route: Get all crops with disease counts
  app.get("/api/crops", (req, res) => {
    const cropsMap: Record<string, number> = {};
    for (const d of diseasesData) {
      cropsMap[d.crop] = (cropsMap[d.crop] || 0) + 1;
    }
    const result = Object.keys(cropsMap).sort().map(crop => ({
      crop,
      disease_count: cropsMap[crop],
      diseases: diseasesData.filter(d => d.crop === crop).map(d => ({
        id: d.disease_id,
        name: d.disease_name,
        pathogen: d.pathogen_type,
      })),
    }));
    res.json({ crops: result, total_crops: result.length, total_diseases: diseasesData.length });
  });

  // API Route: Get diseases list with optional filters
  app.get("/api/diseases", (req, res) => {
    const { crop, search } = req.query;
    let list = diseasesData;
    if (crop && typeof crop === "string") {
      list = list.filter(d => d.crop.toLowerCase() === crop.toLowerCase());
    }
    if (search && typeof search === "string") {
      const q = search.toLowerCase();
      list = list.filter(
        d =>
          d.disease_name.toLowerCase().includes(q) ||
          d.crop.toLowerCase().includes(q) ||
          d.symptoms.toLowerCase().includes(q) ||
          d.pathogen_type.toLowerCase().includes(q)
      );
    }
    res.json({ diseases: list, count: list.length });
  });

  // API Route: Live weather fetch
  app.get("/api/weather/live", async (req, res) => {
    const lat = parseFloat(req.query.lat as string) || 22.57;
    const lon = parseFloat(req.query.lon as string) || 88.36;
    try {
      const weather = await fetchLiveWeather(lat, lon);
      res.json({ success: true, coordinates: { lat, lon }, weather });
    } catch (err: any) {
      res.status(500).json({ error: "Failed to fetch live weather", details: err.message });
    }
  });

  // API Route: Core Advanced Advisory Pipeline (POST /api/advisory/advanced)
  app.post("/api/advisory/advanced", async (req, res) => {
    try {
      const {
        crop,
        disease_name,
        cv_confidence = 0.82,
        latitude = 22.57,
        longitude = 88.36,
        language = "English",
        manual_weather,
      } = req.body;

      if (!crop || !disease_name) {
        return res.status(400).json({
          error: "Missing required fields: 'crop' and 'disease_name' are required",
        });
      }

      // Find database record (case-insensitive search)
      const record = diseasesData.find(
        d =>
          d.crop.toLowerCase() === String(crop).trim().toLowerCase() &&
          d.disease_name.toLowerCase() === String(disease_name).trim().toLowerCase()
      ) || diseasesData.find(
        d => d.crop.toLowerCase() === String(crop).trim().toLowerCase()
      ) || diseasesData[0];

      if (!record) {
        return res.status(404).json({
          error: `No advisory record found for crop '${crop}' and disease '${disease_name}'`,
        });
      }

      // Weather data: either use live or manual override
      let weatherInfo: {
        temperature: number;
        humidity: number;
        rainfall: number;
        windSpeed: number;
        weatherCode: number;
        weatherDescription: string;
        sustainedHighHumidityHours: number;
        source: string;
      };

      if (manual_weather && typeof manual_weather === "object") {
        weatherInfo = {
          temperature: parseFloat(manual_weather.temperature) || 27.0,
          humidity: parseFloat(manual_weather.humidity) || 80.0,
          rainfall: parseFloat(manual_weather.rainfall) || 5.0,
          windSpeed: parseFloat(manual_weather.windSpeed) || 8.0,
          weatherCode: 0,
          weatherDescription: "Manual Scenario Simulation",
          sustainedHighHumidityHours: manual_weather.humidity >= 80 ? 36 : 10,
          source: "User Scenario Simulator",
        };
      } else {
        weatherInfo = await fetchLiveWeather(Number(latitude), Number(longitude));
      }

      // Compute microclimate risk score
      const weatherRisk = computeMicroclimateRisk(
        weatherInfo.humidity,
        weatherInfo.temperature,
        weatherInfo.rainfall,
        record.favorable_conditions,
        weatherInfo.sustainedHighHumidityHours
      );

      // Compute 60/40 composite risk
      const cvConfClamped = Math.max(0, Math.min(1, Number(cv_confidence)));
      const finalRiskScore = Math.round(((0.6 * cvConfClamped) + (0.4 * weatherRisk.score)) * 1000) / 1000;

      let riskLevel: "LOW" | "MEDIUM" | "HIGH";
      let actionUrgency: string;
      if (finalRiskScore < 0.40) {
        riskLevel = "LOW";
        actionUrgency = "Normal preventive schedule. Routine field scouting recommended.";
      } else if (finalRiskScore <= 0.70) {
        riskLevel = "MEDIUM";
        actionUrgency = "Heightened vigilance required. Inspect canopy and apply sanitation measures.";
      } else {
        riskLevel = "HIGH";
        actionUrgency = "Critical risk threshold exceeded. Immediate chemical/bio-fungicide intervention required.";
      }

      // Generate farmer-friendly explanation
      const explanation = await generateFarmerExplanation(
        record,
        riskLevel,
        finalRiskScore,
        {
          temp: weatherInfo.temperature,
          humidity: weatherInfo.humidity,
          rain: weatherInfo.rainfall,
          sustainedHours: weatherInfo.sustainedHighHumidityHours,
        },
        language
      );

      const responsePayload = {
        success: true,
        timestamp: new Date().toISOString(),
        request: {
          crop: record.crop,
          disease_name: record.disease_name,
          cv_confidence: cvConfClamped,
          latitude: Number(latitude),
          longitude: Number(longitude),
          language,
        },
        disease_record: record,
        weather_summary: {
          ...weatherInfo,
          conduciveness_analysis: weatherRisk.details,
        },
        weather_risk_score: weatherRisk.score,
        cv_confidence: cvConfClamped,
        final_risk_score: finalRiskScore,
        risk_level: riskLevel,
        formula_breakdown: `(0.6 × ${cvConfClamped.toFixed(2)}) + (0.4 × ${weatherRisk.score.toFixed(3)}) = ${(0.6 * cvConfClamped).toFixed(3)} + ${(0.4 * weatherRisk.score).toFixed(3)} = ${finalRiskScore.toFixed(3)}`,
        action_urgency: actionUrgency,
        farmer_friendly_explanation: explanation.text,
        llm_generation_source: explanation.source,
      };

      res.json(responsePayload);
    } catch (err: any) {
      console.error("Advisory error:", err);
      res.status(500).json({ error: "Failed to generate advisory", details: err.message });
    }
  });

  // Vite middleware setup
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();

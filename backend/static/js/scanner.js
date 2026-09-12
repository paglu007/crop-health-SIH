/* =========================================
   AI CROP DOCTOR / SCANNER
   ========================================= */

function openScannerModal() {
  document.getElementById('scanner-modal').classList.remove('hidden');
  document.getElementById('scanner-modal').classList.add('flex');
}

function closeScannerModal() {
  document.getElementById('scanner-modal').classList.add('hidden');
  document.getElementById('scanner-modal').classList.remove('flex');
}

async function handleCropUpload(event) {
  const file = event.target.files[0];

  if (!file) {
    return;
  }

  if (!file.type.startsWith("image/")) {
    alert("Please select a valid crop image.");
    return;
  }

  // Show uploaded image immediately
  const img = document.getElementById("scanner-view-img");
  const imageUrl = URL.createObjectURL(file);
  img.src = imageUrl;

  // Show processing state
  const title = document.getElementById("diag-disease-title");
  const conf = document.getElementById("diag-confidence");
  const desc = document.getElementById("diag-desc");

  title.textContent = "Verifying crop image...";
  conf.textContent = "Processing...";
  desc.textContent = "AI model is analyzing the uploaded crop photo.";

  // Prepare image for backend
  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch("/api/diagnosis/verify", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    console.log("Image verification:", data);

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Image verification failed");
    }

    // Display actual model result
    title.textContent = data.disease;
    conf.textContent = `${data.confidence}% Confidence`;
    desc.textContent = data.description || "Disease detected from uploaded crop image.";

  } catch (error) {
    console.error("Image verification failed:", error);

    title.textContent = "Verification failed";
    conf.textContent = "";
    desc.textContent = "The crop image could not be analyzed.";
  }
}

function switchScannerSample(type) {

  const img = document.getElementById('scanner-view-img');
  const title = document.getElementById('diag-disease-title');
  const conf = document.getElementById('diag-confidence');
  const desc = document.getElementById('diag-desc');
  const bio = document.getElementById('diag-bio');
  const chem = document.getElementById('diag-chem');

  if (type === 'yellow_rust') {

    fetch("/api/risk/calculate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        observation_id: 1,
        pathogen_type: "Yellow Rust",
        severity_pct: 30
      })
    })
    .then(response => response.json())
    .then(data => {
      console.log("Real backend risk:", data);

      if (data.success && data.risk) {
        desc.innerHTML = `
          Distinct yellow pustules arranged in linear stripes along the leaf veins.

          <br><br>

          <strong>AI Risk Assessment</strong><br>
          Risk Level: ${data.risk.risk_level}<br>
          Risk Score: ${data.risk.risk_score}

          <br><br>

          <strong>Live Weather</strong><br>
          Temperature: ${data.weather_used.temp_c}°C<br>
          Humidity: ${data.weather_used.humidity_pct}%<br>
          Rainfall: ${data.weather_used.rainfall_mm} mm<br>
          Wind Speed: ${data.weather_used.wind_speed_kph} kph
        `;
      }
    })
    .catch(error => {
      console.error("Risk API failed:", error);
    });

    img.src = 'https://images.unsplash.com/photo-1615811361523-6bd03d7748e7?auto=format&fit=crop&w=800&q=80';
    title.textContent = 'Yellow Rust (Puccinia striiformis)';
    conf.textContent = '96.4% Confidence';
    bio.textContent = 'Spray Neem Seed Kernel Extract (5%) or Trichoderma viride @ 5g/liter.';
    chem.textContent = 'Propiconazole 25% EC @ 1ml/L during morning hours.';

  } else if (type === 'rice_blast') {

    img.src = 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80';
    title.textContent = 'Rice Blast (Magnaporthe oryzae)';
    conf.textContent = '94.8% Confidence';
    desc.textContent = 'Spindle-shaped lesions with gray or white centers and brown margins.';
    bio.textContent = 'Apply Pseudomonas fluorescens 0.2% seed treatment and foliar spray.';
    chem.textContent = 'Tricyclazole 75% WP @ 0.6g/L of water at boot leaf stage.';

  } else if (type === 'healthy') {

    img.src = 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=800&q=80';
    title.textContent = 'Healthy Crop (No Pathogens Detected)';
    conf.textContent = '99.1% Confidence';
    desc.textContent = 'Leaf tissue exhibits optimal chlorophyll density and clean margins.';
    bio.textContent = 'Maintain standard balanced NPK fertilization and irrigation.';
    chem.textContent = 'No chemical intervention needed. Monitor again in 7 days.';
  }
}

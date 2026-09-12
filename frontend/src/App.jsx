import { useState } from 'react'
import './App.css'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '⌂' },
  { id: 'analyze', label: 'AI Crop Doctor', icon: '✦' },
  { id: 'risk', label: 'Disease Risk', icon: '◈' },
  { id: 'weather', label: 'Weather', icon: '☁' },
  { id: 'map', label: 'Farm Map', icon: '⌖' },
  { id: 'reports', label: 'Reports', icon: '▤' },
]

function App() {
  const [activePage, setActivePage] = useState('dashboard')

  return (
    <div className="krishi-app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">🌱</div>
          <div>
            <strong>KrishiRakshak</strong>
            <span>AI Crop Health</span>
          </div>
        </div>

        <nav className="navigation" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => setActivePage(item.id)}
              type="button"
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="ai-status">
            <span className="status-dot" />
            <div>
              <strong>AI System Online</strong>
              <span>Ready for analysis</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">SMART AGRICULTURE PLATFORM</p>
            <h1>Crop Health Command Center</h1>
          </div>

          <div className="topbar-actions">
            <button className="language-button" type="button">
              EN
            </button>
            <button className="profile-button" type="button">
              <span>👨‍🌾</span>
              <span>Farmer</span>
            </button>
          </div>
        </header>

        <section className="page-content">
          <div className="welcome-row">
            <div>
              <p className="section-label">FIELD OVERVIEW</p>
              <h2>Good day, Farmer 👋</h2>
              <p className="muted">
                Monitor your crops, detect disease early, and make informed
                decisions.
              </p>
            </div>

            <button
              className="primary-button"
              type="button"
              onClick={() => setActivePage('analyze')}
            >
              ✦ Analyze Crop
            </button>
          </div>

          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-icon green">🌿</div>
              <div>
                <span>Active Fields</span>
                <strong>3</strong>
              </div>
              <small>Being monitored</small>
            </article>

            <article className="stat-card">
              <div className="stat-icon amber">⚠</div>
              <div>
                <span>Risk Alerts</span>
                <strong>2</strong>
              </div>
              <small>Require attention</small>
            </article>

            <article className="stat-card">
              <div className="stat-icon blue">☁</div>
              <div>
                <span>Weather</span>
                <strong>27.4°C</strong>
              </div>
              <small>87% humidity</small>
            </article>

            <article className="stat-card">
              <div className="stat-icon purple">✓</div>
              <div>
                <span>Health Status</span>
                <strong>Good</strong>
              </div>
              <small>Overall field condition</small>
            </article>
          </div>

          <div className="dashboard-grid">
            <section className="panel analyze-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">AI CROP DOCTOR</p>
                  <h3>Analyze a crop</h3>
                </div>
                <span className="ai-badge">AI Verified</span>
              </div>

              <div className="upload-area">
                <div className="upload-icon">📷</div>
                <h4>Upload a crop image</h4>
                <p>
                  Capture a clear image of the affected leaf or plant for
                  disease analysis.
                </p>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setActivePage('analyze')}
                >
                  Open Crop Doctor
                </button>
              </div>
            </section>

            <section className="panel risk-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">LATEST ASSESSMENT</p>
                  <h3>Disease Risk</h3>
                </div>
                <span className="risk-badge">MEDIUM</span>
              </div>

              <div className="risk-score">
                <strong>49.8</strong>
                <span>/ 100</span>
              </div>

              <div className="progress-track">
                <div className="progress-value" />
              </div>

              <p className="muted">
                Moderate spread risk based on disease severity and current
                environmental conditions.
              </p>
            </section>
          </div>

          <section className="panel advisory-panel">
            <div className="panel-header">
              <div>
                <p className="section-label">SMART ADVISORY</p>
                <h3>Recommended next steps</h3>
              </div>
              <span className="advisory-badge">Field-specific</span>
            </div>

            <div className="advisory-list">
              <div className="advisory-item">
                <span>01</span>
                <div>
                  <strong>Inspect affected plants closely</strong>
                  <p>
                    Increase monitoring while disease risk remains moderate.
                  </p>
                </div>
              </div>

              <div className="advisory-item">
                <span>02</span>
                <div>
                  <strong>Monitor humidity and rainfall</strong>
                  <p>
                    Current conditions may favor fungal disease development.
                  </p>
                </div>
              </div>

              <div className="advisory-item">
                <span>03</span>
                <div>
                  <strong>Review treatment guidance</strong>
                  <p>
                    Use crop- and disease-specific agricultural recommendations.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </section>
      </main>
    </div>
  )
}

export default App
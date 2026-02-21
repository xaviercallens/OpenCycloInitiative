# 🌍 Cyclo-Earth: Project Genesis

The ultimate strategic visualization of the OpenCyclo Initiative. This frontend interface bridges individual user experience with global climate dynamics, allowing anyone to tangibly see the difference 1,000,000 decentralized cycloreactors make on atmospheric chemistry.

## 🛠️ The Simulation Stack
- **Browser-Side Climate Physics**: A localized javascript port (`genesis.js`) of Hector/MAGICC equivalent physics. It calculates biochar latency grids and carbon flux (BAU - PSC model variants) dynamically out to the year 2100.
- **The Golden Cross**: An algorithmic visual threshold that celebrates the exact year the Earth hits "Net Zero" based on user inputs.
- **WebGL Interactivity**: Draws tens of thousands of procedural map data points rendering the simulation entirely locally via the `canvas` context without taxing high bandwidth resources.

Project Genesis is the "Why" to the CV-PBR-V1's "How".

## ☁️ Deploying to Google Cloud Platform (GCP)
For public demonstration of the Planetary Symbiosis Cycle, this repository includes everything needed to instantaneously deploy to Google Cloud Platform:
- `Dockerfile`: Wraps the simulator in an NGINX Alpine lightweight container for **Cloud Run** (massively scalable).
- `app.yaml`: An alternative static-serving configuration for **Google App Engine** (free tier friendly).

### Automated Shell Setup
If you have the `gcloud CLI` installed locally on your system, just run the deployment script to push it live to the internet:
```bash
cd software/cyclo_earth_web
chmod +x deploy_gcp.sh
./deploy_gcp.sh
```
This will allow you to pick the containerized or static deployment and give you a global URL instantly!

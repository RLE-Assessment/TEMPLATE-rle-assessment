# RLE Assessment Template

Template repository for IUCN Red List of Ecosystems assessment reports using Quarto and Google Earth Engine.

## Getting Started

1. Create a new repository from this template
2. Update `config/country_config.yaml` with your country-specific settings
3. Configure GCP authentication (see [docs/GCP_SETUP.md](docs/GCP_SETUP.md))
4. Enable GitHub Pages in repository settings (deploy with **GitHub Actions**)

## Local Development

Install dependencies:
```bash
pixi install
```

Preview the Quarto book:
```bash
pixi run quarto preview
```

Render the book:
```bash
pixi run quarto-render
```

## Configuration

- `config/country_config.yaml` - Country-specific settings (GCP project, ecosystem asset ID)
- `_quarto.yml` - Quarto book configuration

## Documentation

- [GCP Setup Guide](docs/GCP_SETUP.md) - Configure Google Cloud authentication for GitHub Actions

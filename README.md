# OnlyDust Star Tracker

A Streamlit dashboard for analyzing developer contributions in the Starknet ecosystem.

## Features

- Developer classification based on PR contributions
- Global investment distribution visualization
- Filtering by programming languages, categories, and projects
- Cost per developer analysis
- Network distribution analysis (Starknet-exclusive vs multi-chain developers)

## Installation

1. Clone the repository
```bash
git clone https://github.com/YOUR-USERNAME/onlydust-star-tracker.git
cd onlydust-star-tracker
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

1. Place your data file according to the configuration in `config.yaml`

2. Run the Streamlit app:
```bash
streamlit run main.py
```

## Configuration

The application is configured via `config.yaml`. Key settings include:

- Data source path
- Developer category thresholds
- Application display settings

## Dependencies

- streamlit
- pandas
- plotly
- pycountry
- pyyaml

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
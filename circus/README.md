# Circus Job Registration Script

This script automates the registration of job seekers on the circus-job.com website.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials**
   - Copy `config.py` and update it with your actual credentials:
   ```python
   # Login credentials
   EMAIL = "your_actual_email@example.com"
   PASSWORD = "your_actual_password"
   
   # File paths
   CSV_INPUT_PATH = "/Users/rintaro/Downloads/outputdata.csv"
   CSV_OUTPUT_DIR = "/Users/rintaro/Downloads/"
   ```

3. **Prepare CSV Data**
   - Ensure your CSV file has the following columns:
     - `name`: Full name
     - `furigana`: Name in katakana
     - `birthYear`: Birth year
     - `birthMonth`: Birth month
     - `birthDay`: Birth day
     - `postal`: Postal code
     - `address`: Full address
     - `phone`: Phone number
     - `email`: Email address
     - `license`: License information
     - `education`: Education information

## Usage

Run the script:
```bash
python register_with_status_create_button_local.py
```

## Features

- Automatically logs into circus-job.com
- Processes CSV data for job seeker registration
- Tracks registration status in the CSV file
- Saves registration results with timestamps
- Handles browser automation with Selenium

## Security Notes

- The `config.py` file is excluded from version control to protect credentials
- Never commit your actual credentials to the repository
- Consider using environment variables for production deployments

## Troubleshooting

If you encounter issues:
1. Ensure Chrome browser is installed
2. Check that your credentials in `config.py` are correct
3. Verify the CSV file path and format
4. Make sure you have a stable internet connection 
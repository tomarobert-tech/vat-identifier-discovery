"""
Builds the random 300-company sample used throughout this project, from a
Companies House bulk data ZIP file.

IMPORTANT: this script has no fixed random seed, so running it again
produces a DIFFERENT sample than the one already saved in
sample_companies.json. Do not re-run this - the whole document (Part 1,
Part 2) is written around the specific 300 companies already in that file.
"""

import csv
import io
import json
import random
import zipfile

INPUT_ZIP = "BasicCompanyDataAsOneFile-2026-09-01.zip"
OUTPUT_JSON = "sample_companies.json"
SAMPLE_SIZE = 300


def generate_sample_from_zip(zip_path, sample_size=100):
    candidates = []

    print(f"Opening ZIP archive: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as z:
        # find the CSV file name inside the archive
        csv_filename = [f for f in z.namelist() if f.endswith(".csv")][0]
        print(f"CSV file found in archive: '{csv_filename}'. Reading data...")

        with z.open(csv_filename, "r") as f:
            # wrap the binary stream in a UTF-8 text reader - reads row by
            # row, does not load the whole file into memory
            text_file = io.TextIOWrapper(f, encoding="utf-8", errors="ignore")
            reader = csv.reader(text_file)

            raw_header = next(reader)
            header = [col.strip().replace('"', "") for col in raw_header]
            print(f"Real CSV columns: {header[:4]}")

            # find the indices of the columns we need
            name_idx = next(
                (i for i, c in enumerate(header) if "CompanyName" in c), 0
            )
            number_idx = next(
                (i for i, c in enumerate(header) if "CompanyNumber" in c), 1
            )
            status_idx = next(
                (i for i, c in enumerate(header) if "CompanyStatus" in c), 2
            )
            postcode_idx = next(
                (i for i, c in enumerate(header) if "PostCode" in c), -1
            )
            sic_idx = next((i for i, c in enumerate(header) if "SIC" in c), -1)

            for row in reader:
                if not row or len(row) <= max(name_idx, status_idx):
                    continue

                status_value = row[status_idx].strip().upper()

                # keep active companies only
                if "ACTIVE" in status_value:
                    candidates.append({
                        "company_name": row[name_idx].strip(),
                        "company_number": row[number_idx].strip(),
                        "postcode": (
                            row[postcode_idx].strip()
                            if postcode_idx != -1 and len(row) > postcode_idx
                            else ""
                        ),
                        "sic_code": (
                            row[sic_idx].strip()
                            if sic_idx != -1 and len(row) > sic_idx
                            else ""
                        ),
                    })

    print(f"Found {len(candidates)} active companies. Generating the random sample...")

    actual_sample_size = min(sample_size, len(candidates))
    sampled = random.sample(candidates, actual_sample_size)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(sampled, f, indent=4, ensure_ascii=False)

    print(f"Clean sample of {len(sampled)} companies saved to '{OUTPUT_JSON}'!")


if __name__ == "__main__":
    generate_sample_from_zip(INPUT_ZIP, SAMPLE_SIZE)
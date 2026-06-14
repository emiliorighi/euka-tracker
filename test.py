import requests
gh_url = "https://raw.githubusercontent.com/apollo994/BUSCO-tracker/refs/heads/dev/BUSCO/eukaryota_odb12/BUSCO.tsv"


"""
busco score check:
-> completed+fragmented+missing=100%
-> single+duplicted=completed

"""
# TSV fields: annotation_id	lineage	busco_count	complete	single	duplicated	fragmented	missing
# Don't stream: chunk boundaries can split lines and iter_lines() then yields partial rows (e.g. 6 cols instead of 8).
not_valid_rows = []
response = requests.get(gh_url)
response.raise_for_status()
text = response.text
# Normalize CRLF so splitlines() gives one line per row
lines = text.strip().replace("\r\n", "\n").replace("\r", "\n").split("\n")
tsv_header = lines[0]
print(tsv_header)
for line in lines[1:]:
    row = line.split("\t")
    if len(row) != 8:
        print(f"Skipping malformed row ({len(row)} columns): {line[:80]}...")
        continue
    complete, single, duplicated, fragmented, missing = row[3:8]
    # round numbers to int
    complete = int(round(float(complete)))
    single = int(round(float(single)))
    duplicated = int(round(float(duplicated)))
    fragmented = int(round(float(fragmented)))
    missing = int(round(float(missing)))
    sum = complete + fragmented + missing
    if sum == 100 or sum == 101 or sum == 99:
        continue
    else:
        not_valid_rows.append(line)
print(len(not_valid_rows))

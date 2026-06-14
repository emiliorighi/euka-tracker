


"""

Use mapped_locations_mexico.jsonl and datasets-eukaryotes.jsonl to get the organisms from the samples

"""
import json 


collected_accessions = []

with open('mapped_locations_mexico.jsonl', 'r') as file:
    for line in file:
        data = json.loads(line)
        assembly_accession = data['assembly_accession']
        collected_accessions.append(assembly_accession)

collected_organisms = []
unique_taxids = set()
with open('datasets-eukaryotes.jsonl', 'r') as file:
    for line in file:
        data = json.loads(line)
        accession = data['accession']
        if accession in collected_accessions:
            organism = data['organism']
            taxid = organism['tax_id']
            unique_taxids.add(taxid)
            name = organism['organism_name']
            collected_organisms.append((accession, taxid, name))

print(len(unique_taxids))
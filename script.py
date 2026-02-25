import requests



response = requests.get("https://genome.crg.es/annotrieve/api/v0/annotations/frequencies/taxid")


print(len(response.json().keys()))
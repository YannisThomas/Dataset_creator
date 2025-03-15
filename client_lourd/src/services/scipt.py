# Script pour générer le mapping des classes
from pathlib import Path
import json

# Lire les classes depuis le fichier annotations.txt
annotations_file = Path("annotations.txt")
with open(annotations_file, 'r', encoding='utf-8') as f:
    classes = [line.strip() for line in f if line.strip()]

# Créer le mapping (class_name -> class_id)
class_mapping = {}
for i, class_name in enumerate(classes):
    class_mapping[class_name] = i

# Sauvegarder dans le fichier de configuration
config_dir = Path("client_lourd/src/config")
config_dir.mkdir(parents=True, exist_ok=True)
config_file = config_dir / "mapillary_config.json"

# Charger la configuration existante si elle existe
config = {}
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

# Mettre à jour le mapping des classes
config['class_mapping'] = class_mapping

# Sauvegarder la configuration
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"Mapping des classes généré avec succès: {len(classes)} classes")
# Dataset Creator - Dataset Management System

An MVC architecture application for managing, importing and exporting datasets, with a focus on image annotation datasets.

## Features

- **Dataset Management**: Create, update, and manage datasets with customizable classes
- **Import Capabilities**: Import datasets from local directories and external APIs
- **Export Options**: Export datasets to various formats (YOLO, etc.)
- **API Integration**: Connect to external APIs like Mapillary for data retrieval
- **Validation**: Validate datasets before import/export to ensure data integrity

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YannisLamamoce/Dataset_creator.git
cd client_lourd
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - Windows:
```bash
venv\Scripts\activate
```
   - macOS/Linux:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration file:
```bash
cp config.example.json config.json
```

2. Edit `config.json` with your settings

## Usage

### Running the Application

```bash
python src/main.py
```

### Creating a New Dataset

```python
from src.controllers.dataset_controller import DatasetController

controller = DatasetController()
dataset = controller.create_dataset(
    name="my_dataset",
    classes={0: "class1", 1: "class2"}
)
```

### Importing Data

```python
from src.controllers.import_controller import ImportController

controller = ImportController()
dataset = controller.import_from_local(
    source_path="path/to/images",
    dataset_name="my_dataset",
    format="YOLO"
)
```

### Exporting Data

```python
from src.controllers.export_controller import ExportController

controller = ExportController()
export_path = controller.export_dataset(
    dataset=dataset,
    export_format="YOLO",
    output_path="path/to/export"
)
```

## Project Structure

```
client_lourd/
├── src/
│   ├── controllers/        # MVC controllers
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   ├── utils/              # Utility functions and classes
│   ├── views/              # UI components
│   └── main.py             # Application entry point
├── tests/                  # Unit and integration tests
├── data/                   # Data storage directory
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## License

[Specify your license]

## Contributors

[List of contributors]

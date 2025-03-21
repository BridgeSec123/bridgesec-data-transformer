# Bridgesec Data Transformer

## Project OverviewBridgesec Data Transformer is a Django-based project that interacts with Okta APIs, processes data, and stores extracted information in MongoDB. The project efficiently manages multiple Okta entities.

## Folder Structure
```
bridgesec_data_transformer/
│── .env
│── .env.example
│── .gitignore
│── manage.py
│── requirements.txt
│── db.sqlite3
│── bridgesec_data_transformer/        # Project-level package
│   │── __init__.py
│   │── settings.py                     # Django settings
│   │── urls.py                          # Project-level URL configurations
│   │── wsgi.py                          # WSGI entry point
│   │── asgi.py                          # ASGI entry point
│── core/                                # Main application
│   │── __init__.py
│   │── admin.py                         # Admin panel configurations
│   │── apps.py                          # Application configuration
│   │── urls.py                          # Core URL configurations
│   │── views/                           # Maintains all entity ViewSets handling API logic
│   │   │── __init__.py
│   │   │── base.py                     # Base ViewSet for reusability
│   │   │── user_views.py               # Handles User entity API views
│   │   │── group_views.py              # Handles Group entity API views
│   │   │── other_entities_views.py     # Handles Other Okta entity API views
│   │── serializers/                     # Serializers for transforming API responses
│   │   │── __init__.py
│   │   │── base_serializer.py          # Base serializer for common transformations
│   │   │── user_serializer.py          # Handles User entity serialization
│   │   │── group_serializer.py         # Handles Group entity serialization
│   │   │── other_entities_serializer.py # Handles Other entity serialization
│   │── models/                          # Defines database models for different entities
│   │   │── __init__.py
│   │   │── base_model.py                # Base model for shared database fields
│   │   │── user.py                      # Defines User model schema
│   │   │── group.py                     # Defines Group model schema
│   │── utils/                           # Utility functions and helper scripts
│   │   │── __init__.py
│   │   │── entity_mapping.py           # Maps Okta API responses to internal structure
│   │   │── pagination.py               # Custom pagination logic for API responses
│   │   │── rate_limit.py               # Implements rate-limiting for API requests
│   │── migrations/                      # Django migrations for database updates
│   │   │── __init__.py
│── output/                              # Stores processed data output
│── logs/                                # Stores application logs
```

## How to Run the Application

### Prerequisites
- Python 3.12
- pip (Python package manager)
- Virtual environment (recommended)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone <github-repository-url>
   cd bridgesec_data_transformer
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   - Copy the `.env.example` file to `.env` and configure it accordingly.
5. Run the application:
   ```bash
   python manage.py runserver
   ```
6. Access the API at:
   ```
   http://127.0.0.1:8000/
   ```

## Logging
Logs are stored in the `logs/` directory. Ensure this folder is present before running the application to avoid errors.

## Output Storage
Processed data is stored in the `output/` directory.

## Contributing
Feel free to submit issues and pull requests.

## License
MIT License.


# seis_proc_db

## Database for Yellowstone earthquake information, primarily from deep-learning methods.

## Structure
<pre>
seis-proc-db/  
│ 
├── docs/                       # Contains ER diagrams
├── src/                        # use src layout  
|   └──seis_proc_db/            # Main app code (models, services, etc.)  
│       ├── __init__.py    
│       ├── config.py           # Configuration file   
│       ├── tables.py           # Database tables   
│       ├── services.py         # Business logic    
│       ├── database.py         # Engine, session, base setup    
|       └── pytables_backend.py # Pytables for storing arrays on disk 
│  
├── scripts/                     # Database-related scripts   
│   ├── add_stations_channels.py # Add station and channel info to the db from xml files
│   ├── build_tables.py          # Script to create tables   
│   └── drop_tables.py           # Script to drop tables   
│    
├── tests/                       # seis_proc_db pytests  
|   ├── __init__.py 
│   ├── conftest.py              # To share fixtures across multiple files (e.g., building a db session)
│   ├── test_tables.py           # Tests for seis_proc_db.tables
│   ├── test_services.py         # Tests for serivices.py
│   └── test_pytables_backend.py # Tests for pytables_backend.py
| 
├── pyproject.toml               # Used to set up the python env
└── README.md                    # Documentation   

</pre>
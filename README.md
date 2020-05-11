# Review Analysis - back end
Key functionality si bound to repository [Review analysis](https://github.com/AndrejKlocok/review_analysis), with which objects it communicates and
provides API for them. Part of the system is front end application [Review analysis-front end](https://github.com/AndrejKlocok/review_analysis-frontend).

All these repositories needs to be in the same directory. Key python requirements are described in [Review analysis](https://github.com/AndrejKlocok/review_analysis).

## Build
API needs at least 50GB of RAM memory to be able to load all models.

## Execution
Before execution the flask command needs to be configured with this command:

        export FLASK_APP=run.py 

Start backend server with command (on pcknot5 server):

        flask run --host=0.0.0.0 --port=42024

## Documentation
API is documented by swagger on entry endpoint:
        
        http://pcknot5.fit.vutbr.cz:42024/

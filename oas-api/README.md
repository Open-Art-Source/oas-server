#initial setup

This is a standard pythong/flask project. We recommend virtual environment for easy self-contained project but that is not a must. installation of dependencies is via standard 'pip install -r requirements.txt'

#dependencies

The project use Mysql/Mariadb as the backend for transactional data and ipfs to store NFT related data(metadata). Initialization of database structure is done by running oas/oas_schema.sql against an empty db. 

#run the server

all parameters are setup through environment variables which can either be wrapped inside standard shell script or via dotnev file. from the command line, just run 'python application.py'

#AWS elasticbeanstalk

special setup has been given to support AWS elasticbeanstalk by zipping everything into a zip file and create a new EB app. The supplied files(under .ebextension and .platform) will do all the necessary setup including letsencrypt setup for secure https connection to the API server

#environment parameters

there is a set of default settings in oas/config.py but can be overridden either by dotenv file or actual environment variables(that depends on how the project is deployed and run)

#test console

There is a default website page that can act as a 'api test' console to test out the json-rpc api(/test). It also contains a brief list of all the api calls implemented(for mobile app integration use)
# Clue

To start the API for clue, check to ensure that:

1. Docker is composed up through `dev/docker-compose.yml`
2. `cd clue/api`
3. Run `poetry install` within the clue/api folder to install all dependencies
4. You may need to run `poetry install --with test,dev,types,plugins --all-extras`
5. Run `sudo mkdir -p /var/log/clue/`
6. Run `sudo mkdir -p /etc/clue/conf/`
7. Run `sudo chmod a+rw /var/log/clue/`
8. Run `sudo chmod a+rw /etc/clue/conf/`
9. Run `cp build_scripts/classification.yml /etc/clue/conf/classification.yml`
10. Run `cp test/unit/config.yml /etc/clue/conf/config.yml`
11. To start server: `poetry run server`

To start Enrichment Testing:

* In order to have the local server connect to the UI the servers need to be ran manually
* Please ensure that ```pwd``` is clue/api
* May need to add ```poetry run``` before each command

1. ```flask --app test.utils.test_server run --no-reload --port 5008```
2. ```flask --app test.utils.bad_server run --no-reload --port 5009```
3. ```flask --app test.utils.slow_server run --no-reload --port 5010```
4. ```flask --app test.utils.telemetry_server run --no-reload --port 5011```

Troubleshooting:

1. If there are issues with these steps please check the build system for poetry installation steps
2. The scripts will show all necessary directories that need to be made in order for classfication to work

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.en.md) for more information

## FAQ

### I'm getting permissions issues on `/var/log/clue` or `/etc/clue/conf`?

Run `sudo chmod a+rw /var/log/clue/` and `sudo chmod a+rw /etc/clue/conf/`.

### How can I add dependencies for my plugin?

See [this section](docs/CONTRIBUTING.en.md#external-dependencies) of CONTRIBUTING.md.

### Email rendering does not seem to be working?

You must install `wkhtmltopdf`, both locally for development and in your Dockerfile:

```bash
sudo apt install wkhtmltopdf
```

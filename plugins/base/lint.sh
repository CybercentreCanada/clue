echo "Validating base.Dockerfile"
docker run --rm -i hadolint/hadolint < base.Dockerfile

echo "\nValidating plugin.Dockerfile"
docker run --rm -i hadolint/hadolint < plugin.Dockerfile

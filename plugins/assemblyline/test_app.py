from app import plugin

# Run the plugin locally for testing purposes
if __name__ == "__main__":
    plugin.app.run(host="0.0.0.0", port=5100, debug=True, threaded=False)  # noqa: S104

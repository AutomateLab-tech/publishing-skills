# Publishing Skills maintenance guide

Install only the skills you need. Research sources first, validate the article bundle, then select the matching publishing adapter. A CMS without a shipped adapter requires integration work, not just an API key.

## Installation and compatibility

Follow the repository README for the supported install method and runtime. Pin the version used in a reproducible example. Keep credentials in your client configuration, outside shared fixtures.

## Verify a change

Record the package or snapshot version, exact input, observation time and actual output. Check a materially different input and a valid neighboring case. Treat expected output as a fixture, not a live measurement.

# ho-so-ai

Form work starts on `feature/kim-form`. See the [form scope, open inputs, and agent handoff](docs/form-workstream.md).

See the [proposed PII security and privacy design](docs/security-and-privacy.md) for data flow, encryption, minimization, retention, and planned security checks. These protections are not implemented yet.

## Synthetic forms prototype

A runnable first slice is available in [prototypes/forms](prototypes/forms/README.md).
It uses synthetic data and exports a JSON review copy; official PDFs and user authentication are not implemented yet.

```sh
node --test prototypes/forms/state.test.mjs
node prototypes/forms/serve.mjs
```

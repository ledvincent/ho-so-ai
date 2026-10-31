// Provisional internal API. Adapters must authorize sessions and resolve current answers.
export class FormSession {
  #fields;
  #templateVersion;
  #generation = 0;
  #revision = 0;
  #sessionId = null;
  #phase = 'idle';
  #values = {};
  #load = null;
  #export = null;
  #document = null;
  #checkedRevision = null;
  #error = null;

  constructor(fields, { templateVersion = 'synthetic-v1' } = {}) {
    if (!Array.isArray(fields) || fields.length === 0) throw new TypeError('Fields are required.');
    const ids = new Set();
    this.#fields = Object.freeze(fields.map((field) => {
      if (!field || typeof field.id !== 'string' || !/^[a-z][a-z0-9_]*$/i.test(field.id) || ids.has(field.id)) {
        throw new TypeError('Field IDs must be unique identifiers.');
      }
      if (typeof field.label !== 'string' || !field.label.trim()) throw new TypeError('Field labels are required.');
      if (field.maxLength !== undefined && (!Number.isInteger(field.maxLength) || field.maxLength < 1)) {
        throw new TypeError('maxLength must be a positive integer.');
      }
      ids.add(field.id);
      return Object.freeze({ id: field.id, label: field.label, required: Boolean(field.required), maxLength: field.maxLength });
    }));
    this.#templateVersion = this.#version(templateVersion);
  }

  get fields() { return this.#fields; }

  #version(value) {
    if (typeof value !== 'string' || !value.trim()) throw new TypeError('A version is required.');
    return value;
  }

  #invalidate() {
    this.#export = null;
    this.#document = null;
    this.#checkedRevision = null;
    this.#error = null;
  }

  #ready() {
    if (this.#phase !== 'ready') throw new Error('Load a session first.');
  }

  #normalize(values) {
    if (!values || typeof values !== 'object' || Array.isArray(values)) throw new TypeError('Values must be a field map.');
    const allowed = new Set(this.#fields.map((field) => field.id));
    if (Object.keys(values).some((id) => !allowed.has(id))) throw new TypeError('Unknown field in values.');
    return Object.fromEntries(this.#fields.map(({ id }) => {
      const value = Object.hasOwn(values, id) ? values[id] : '';
      if (value !== null && typeof value !== 'string') throw new TypeError('This prototype accepts text fields only.');
      return [id, value ?? ''];
    }));
  }

  #errors() {
    if (this.#phase !== 'ready') return {};
    return Object.fromEntries(this.#fields.flatMap((field) => {
      const value = this.#values[field.id];
      if (field.required && !value.trim()) return [[field.id, 'This field is required.']];
      if (field.maxLength && [...value].length > field.maxLength) return [[field.id, `Use at most ${field.maxLength} characters.`]];
      return [];
    }));
  }

  snapshot() {
    const errors = Object.freeze(this.#errors());
    return Object.freeze({
      sessionId: this.#sessionId, generation: this.#generation, revision: this.#revision,
      templateVersion: this.#templateVersion, phase: this.#phase,
      values: Object.freeze({ ...this.#values }), errors,
      valid: this.#phase === 'ready' && Object.keys(errors).length === 0,
      checked: this.#phase === 'ready' && this.#checkedRevision === this.#revision,
      exporting: this.#export !== null, error: this.#error,
    });
  }

  clear() {
    this.#generation += 1;
    this.#revision = 0;
    this.#sessionId = null;
    this.#phase = 'idle';
    this.#values = {};
    this.#load = null;
    this.#invalidate();
  }

  beginLoad(sessionId) {
    if (typeof sessionId !== 'string' || !sessionId.trim()) throw new TypeError('A session ID is required.');
    this.clear();
    this.#sessionId = sessionId;
    this.#phase = 'loading';
    this.#load = Object.freeze({ generation: this.#generation });
    return this.#load;
  }

  finishLoad(token, values) {
    if (token !== this.#load || token === null) return false;
    const normalized = this.#normalize(values);
    this.#values = normalized;
    this.#phase = 'ready';
    this.#revision += 1;
    this.#load = null;
    this.#invalidate();
    return true;
  }

  failLoad(token) {
    if (token !== this.#load || token === null) return false;
    this.#phase = 'error';
    this.#load = null;
    this.#values = {};
    this.#invalidate();
    this.#error = 'The session could not be loaded. Retry.';
    return true;
  }

  replaceAnswers(values) {
    this.#ready();
    const normalized = this.#normalize(values);
    this.#values = normalized;
    this.#revision += 1;
    this.#invalidate();
  }

  edit(id, value) {
    this.#ready();
    if (!this.#fields.some((field) => field.id === id)) throw new TypeError('Unknown field.');
    if (typeof value !== 'string') throw new TypeError('Field values must be text.');
    if (value === this.#values[id]) return;
    this.#values = { ...this.#values, [id]: value };
    this.#revision += 1;
    this.#invalidate();
  }

  setTemplateVersion(version) {
    const next = this.#version(version);
    if (next === this.#templateVersion) return;
    this.#templateVersion = next;
    this.#revision += 1;
    this.#invalidate();
  }

  confirmValues() {
    this.#ready();
    if (Object.keys(this.#errors()).length) throw new Error('Correct the validation errors first.');
    this.#checkedRevision = this.#revision;
  }

  revokeConfirmation() { this.#invalidate(); }

  beginExport() {
    const snapshot = this.snapshot();
    if (!snapshot.valid || !snapshot.checked) throw new Error('Check the current valid preview before exporting.');
    const token = Object.freeze({ generation: this.#generation, revision: this.#revision });
    this.#export = token;
    this.#document = null;
    this.#error = null;
    return Object.freeze({ token, snapshot });
  }

  finishExport(token, { blob, filename }) {
    if (token !== this.#export || token === null) return false;
    if (!(blob instanceof Blob) || blob.size === 0 || !blob.type) throw new TypeError('A nonempty typed document Blob is required.');
    if (typeof filename !== 'string' || !/^[a-z0-9][a-z0-9_.-]*$/i.test(filename)) throw new TypeError('Use a safe document filename.');
    this.#document = Object.freeze({ blob, filename, sessionId: this.#sessionId, revision: this.#revision, templateVersion: this.#templateVersion });
    this.#export = null;
    return true;
  }

  failExport(token) {
    if (token !== this.#export || token === null) return false;
    this.#export = null;
    this.#document = null;
    this.#error = 'The review copy could not be prepared. Retry.';
    return true;
  }

  document() { return this.#document; }
}

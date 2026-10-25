import React, {useMemo, useRef, useState} from 'react';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {ArrowRight, FileJson, Play, Plus, Trash2} from 'lucide-react';
import {Badge, Button, Empty, ErrorNotice, Field, InlineNote, Loading, PageHead, Panel} from '@arc/ui';
import {bytes, credits} from '@arc/client';
import {buildPlaygroundRequest, discoverFields, PlaygroundInputError} from '@arc/client/playground';
import type {FieldMapping, PlaygroundOperation} from '@arc/client/playground';
import {api, projectPath, useApi, useScope} from '../../../app/platform';
import {ExecutionDetail} from '../../executions/pages/Executions';

const operationInfo: {id: PlaygroundOperation; name: string; description: string}[] = [
  {id: 'validate', name: 'Validate JSON', description: 'Check required fields without changing the input.'},
  {id: 'normalize', name: 'Normalize records', description: 'Trim text, rename fields, and lowercase selected output fields.'},
  {id: 'csv_to_json', name: 'CSV → JSON', description: 'Convert CSV records with a header row to JSON.'},
  {id: 'json_to_csv', name: 'JSON → CSV', description: 'Export JSON records to CSV with spreadsheet-formula protection.'},
];
const sample = '[\n  {"name": " Ada Lovelace ", "email": " ADA@EXAMPLE.COM "},\n  {"name": " Grace Hopper ", "email": " GRACE@EXAMPLE.COM "}\n]';
const csvSample = 'name,email\nAda,ada@example.com\nGrace,grace@example.com';
const starterMappings: FieldMapping[] = [];

type RequestBody = ReturnType<typeof buildPlaygroundRequest>;

export function Playground() {
  const scope = useScope();
  const cache = useQueryClient();
  const requestRevision = useRef(0);
  const [operation, setOperation] = useState<PlaygroundOperation>('normalize');
  const [input, setInput] = useState(sample);
  const [inputMode, setInputMode] = useState<'inline' | 'file'>('inline');
  const [fileId, setFileId] = useState('');
  const [requiredFields, setRequiredFields] = useState('');
  const [lowercaseFields, setLowercaseFields] = useState('email');
  const [mappings, setMappings] = useState<FieldMapping[]>(starterMappings);
  const [maxCredits, setMaxCredits] = useState('10');
  const [formError, setFormError] = useState('');
  const [quote, setQuote] = useState<any>(null);
  const [run, setRun] = useState<any>(null);

  const services = useApi(['services'], '/services');
  const supported = services.data?.items?.find((item: any) => item.id === 'data' && item.status === 'available');
  const allowedIds: string[] = Array.isArray(supported?.operations) ? supported.operations : [];
  const availableOperations = operationInfo.filter(item => allowedIds.includes(item.id));
  const fields = useMemo(() => discoverFields(input, operation), [input, operation]);

  const files = useApi(
    ['files', scope.pid, scope.environment],
    `/projects/${scope.pid}/files?environment=${scope.environment}`,
    inputMode === 'file',
  );
  const matchingFiles = ((files.data?.items || []) as any[]).filter(file => {
    const expiresAt = Number(file.expires_at || 0);
    if (file.state !== 'ready' || expiresAt * 1000 <= Date.now()) return false;
    if (operation === 'csv_to_json') return file.content_type === 'text/csv' || file.content_type === 'text/plain';
    return file.content_type === 'application/json' || file.content_type === 'text/plain';
  });

  const estimate = useMutation({
    mutationFn: ({body}: {body: RequestBody; revision: number}) =>
      api.request(`/projects/${scope.pid}/quote?environment=${scope.environment}`, {method: 'POST', json: body}),
    onSuccess: (result, variables) => {
      if (variables.revision === requestRevision.current) setQuote(result);
    },
  });
  const execute = useMutation({
    mutationFn: (body: RequestBody) =>
      api.request(`/projects/${scope.pid}/jobs?environment=${scope.environment}`, {
        method: 'POST', json: body, headers: {'Idempotency-Key': crypto.randomUUID()},
      }),
    onSuccess: result => {
      setRun(result.job);
      void cache.invalidateQueries({queryKey: ['jobs', scope.pid]});
      void cache.invalidateQueries({queryKey: ['billing']});
    },
  });

  function changed() {
    requestRevision.current += 1;
    setFormError('');
    setQuote(null);
    estimate.reset();
    execute.reset();
  }

  function changeOperation(id: PlaygroundOperation) {
    changed();
    setOperation(id);
    setInput(id === 'csv_to_json' ? csvSample : sample);
    setFileId('');
    setMappings([]);
  }

  function updateMapping(index: number, key: keyof FieldMapping, value: string) {
    changed();
    setMappings(previous => previous.map((mapping, i) => i === index ? {...mapping, [key]: value} : mapping));
  }

  function submit(kind: 'quote' | 'run') {
    try {
      if (!availableOperations.some(item => item.id === operation)) {
        throw new PlaygroundInputError('This operation is not available in the current service catalog.');
      }
      const body = buildPlaygroundRequest({
        operation, input, fileId: inputMode === 'file' ? fileId : undefined,
        requiredFields, lowercaseFields, mappings, maxCredits,
      });
      if (inputMode === 'file' && !matchingFiles.some(file => file.id === fileId)) {
        throw new PlaygroundInputError('Select a verified file compatible with this operation.');
      }
      setFormError('');
      if (kind === 'quote') estimate.mutate({body, revision: requestRevision.current});
      else {
        setRun(null);
        execute.mutate(body);
      }
    } catch (error) {
      setFormError(error instanceof PlaygroundInputError ? error.message : 'Please review the input and try again.');
    }
  }

  if (services.isLoading) return <Loading label="Loading available operations"/>;
  if (services.error) return <ErrorNotice error={services.error}/>;

  return <>
    <PageHead eyebrow="DEVELOPER TOOLS" title="Playground"
      description="Run supported services against your own input, inspect each field, and follow real execution."
      action={<Badge tone={scope.environment === 'test' ? 'warning' : 'success'}>{scope.environment} environment</Badge>}/>
    <div className="playground-layout">
      <Panel>
        <div className="panel-body stack">
          <Field label="Operation">
            <select value={availableOperations.some(item => item.id === operation) ? operation : ''}
              onChange={event => changeOperation(event.target.value as PlaygroundOperation)}>
              {!availableOperations.some(item => item.id === operation) && <option value="">Select an operation</option>}
              {availableOperations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </Field>
          <p className="muted small">{operationInfo.find(item => item.id === operation)?.description}</p>
          {availableOperations.length === 0 && <InlineNote>Processing operations are not enabled for this project.</InlineNote>}
          <Field label="Input source">
            <select value={inputMode} onChange={event => {changed(); setInputMode(event.target.value as 'inline' | 'file'); setFileId('');}}>
              <option value="inline">Enter input</option>
              <option value="file">Previously uploaded file</option>
            </select>
          </Field>
          {inputMode === 'inline' ? <>
            <Field label={operation === 'csv_to_json' ? 'CSV input' : 'JSON input'} hint="Maximum inline payload: 1.5 MB. Use synthetic data for tests.">
              <textarea className="code-input" spellCheck={false} value={input} rows={12}
                onChange={event => {changed(); setInput(event.target.value);}}/>
            </Field>
            {fields.length > 0 && <div className="playground-detected-fields">
              <span className="muted small">Detected fields</span>
              <div className="playground-field-list">{fields.map(name => <code key={name}>{name}</code>)}</div>
            </div>}
          </> : <>
            <Field label="Verified file" hint="Only files already verified in the selected project and environment are eligible.">
              <select value={matchingFiles.some(file => file.id === fileId) ? fileId : ''}
                disabled={files.isLoading}
                onChange={event => {changed(); setFileId(event.target.value);}}>
                <option value="">Choose a compatible file</option>
                {matchingFiles.map(file => <option value={file.id} key={file.id}>{file.name} ({bytes(file.size)})</option>)}
              </select>
            </Field>
            {files.error && <ErrorNotice error={files.error}/>}
            {matchingFiles.length === 0 && !files.isLoading && <InlineNote>No compatible verified files yet. Upload a JSON or CSV file on the <a href={projectPath(scope.wid, scope.pid, scope.environment, 'files')}>Files page</a>.</InlineNote>}
          </>}
          {operation === 'validate' && <Field label="Required fields" hint="Comma-separated names. Every record must contain these fields.">
            <input value={requiredFields} placeholder="name, email" onChange={event => {changed(); setRequiredFields(event.target.value);}}/>
          </Field>}
          {operation === 'normalize' && <>
            <Field label="Lowercase output fields" hint="Comma-separated field names. If you rename a field, use its NEW name here.">
              <input value={lowercaseFields} placeholder="email" onChange={event => {changed(); setLowercaseFields(event.target.value);}}/>
            </Field>
            <section className="playground-mappings" aria-label="Field mappings">
              <div className="flow-between">
                <div><strong>Rename fields</strong><p className="small muted">Map input field names to their desired output names.</p></div>
                <Button variant="secondary" onClick={() => {changed(); setMappings(old => [...old, {source:'', target:''}]);}} disabled={mappings.length >= 64}>
                  <Plus size={14}/>Add field
                </Button>
              </div>
              {mappings.map((entry, index) => <div className="playground-mapping-row" key={index}>
                <input aria-label={`Source field ${index + 1}`} list="playground-fields" placeholder="Original field"
                  value={entry.source} onChange={event => updateMapping(index, 'source', event.target.value)}/>
                <ArrowRight size={16} aria-hidden="true"/>
                <input aria-label={`Destination field ${index + 1}`} placeholder="Output field"
                  value={entry.target} onChange={event => updateMapping(index, 'target', event.target.value)}/>
                <button className="icon-button" aria-label={`Remove mapping ${index + 1}`} onClick={() => {changed(); setMappings(old => old.filter((_, i) => i !== index));}}><Trash2 size={15}/></button>
              </div>)}
              <datalist id="playground-fields">{fields.map(name => <option value={name} key={name}/>)}</datalist>
              {mappings.length === 0 && <p className="muted small">No mappings yet. Existing field names will be kept.</p>}
            </section>
          </>}
          <Field label="Maximum credits per execution" hint="The server determines the actual charge before admitting the job.">
            <input type="number" min="0" max="1000" step="0.001" value={maxCredits}
              onChange={event => {changed(); setMaxCredits(event.target.value);}}/>
          </Field>
          {formError && <p role="alert" className="error-text">{formError}</p>}
          {estimate.error && <ErrorNotice error={estimate.error}/>}
          {execute.error && <ErrorNotice error={execute.error}/>}
          <div className="form-actions">
            <Button variant="secondary" busy={estimate.isPending} disabled={!availableOperations.length} onClick={() => submit('quote')}>Preview cost</Button>
            <Button busy={execute.isPending} disabled={!availableOperations.length} onClick={() => submit('run')}><Play size={14}/>Run operation</Button>
          </div>
        </div>
      </Panel>
      <div className="stack">
        {quote && <Panel title="Cost preview"><div className="panel-body">
          <div className="credit-number">{credits(quote.estimated_milli)}<small>credits</small></div>
          <p className="muted">{bytes(quote.input_bytes)} input · price version {quote.price_version}</p>
          <InlineNote>{quote.is_test ? 'Test credits have no cash value.' : 'Credits are reserved before processing and settled after a valid result.'}</InlineNote>
        </div></Panel>}
        {run ? <ExecutionDetail jobId={run.id}/> : <Panel><Empty icon={<FileJson size={24}/>} title="Your result starts here"
          description="Choose an operation and send a request. This view shows actual processing events, not a recorded animation."/></Panel>}
        <InlineNote>Public integrations use a server-side API key. This Playground uses your authenticated portal session.</InlineNote>
      </div>
    </div>
  </>;
}

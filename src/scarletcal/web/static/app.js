'use strict';
const apiOrigin = window.SCARLETCAL_API_ORIGIN || '';
const apiUrl = path => apiOrigin + path;
const form = document.querySelector('#schedule-form');
const fields = document.querySelector('#fields');
const schedule = document.querySelector('#schedule');
const term = document.querySelector('#term');
const standard = document.querySelector('#standard');
const status = document.querySelector('#status');
const generate = document.querySelector('#generate');
const download = document.querySelector('#download');
const retry = document.querySelector('#retry');
let terms = [];
let downloadUrl;

function message(text, kind = '') {
  status.textContent = text;
  status.className = kind;
}
function clearDownload() {
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = undefined;
  download.hidden = true;
  download.removeAttribute('href');
}
async function request(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(url, {...options, signal: controller.signal, credentials: 'omit'});
    const body = await response.blob();
    return new Response(body, {status: response.status, statusText: response.statusText, headers: response.headers});
  } finally {
    clearTimeout(timeout);
  }
}
function showDates() {
  const selected = terms.find(item => item.id === term.value);
  document.querySelector('#term-dates').textContent = selected
    ? `Regular classes: ${selected.instruction_start} to ${selected.instruction_end}` : '';
}
async function loadTerms() {
  fields.disabled = true;
  retry.hidden = true;
  message('Loading supported semesters…');
  try {
    const response = await request(apiUrl('/api/terms'));
    if (!response.ok) throw new Error('Cannot load semesters.');
    terms = await response.json();
    if (!Array.isArray(terms) || !terms.length) throw new Error('No semesters available.');
    term.replaceChildren(...terms.map(item => new Option(item.label, item.id)));
    showDates();
    fields.disabled = false;
    message('');
  } catch {
    message('Couldn’t load semesters. Check your connection and try again.', 'error');
    retry.hidden = false;
  }
}
retry.addEventListener('click', loadTerms);
term.addEventListener('change', showDates);
form.addEventListener('input', () => { clearDownload(); message(''); });
document.querySelector('#sample').addEventListener('click', async () => {
  fields.disabled = true;
  clearDownload();
  try {
    const response = await request('./static/example.txt');
    if (!response.ok) throw new Error('Sample unavailable.');
    schedule.value = await response.text();
    message('Sample loaded: four courses. Choose a semester and confirm the calendar below.');
  } catch {
    message('Couldn’t load the sample. You can still paste your WebReg schedule.', 'error');
  } finally {
    fields.disabled = false;
    schedule.focus();
  }
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  if (!schedule.value.trim()) {
    message('Paste your registered WebReg courses before generating a calendar.', 'error');
    schedule.focus();
    return;
  }
  const payload = {schedule: schedule.value, term: term.value, standard_calendar: standard.checked};
  clearDownload();
  fields.disabled = true;
  form.setAttribute('aria-busy', 'true');
  generate.textContent = 'Building your calendar…';
  message('Checking your schedule and generating class events…');
  try {
    const response = await request(apiUrl('/api/calendar'), {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Calendar generation failed. Please try again.');
    }
    if (!response.headers.get('Content-Type')?.startsWith('text/calendar')) {
      throw new Error('The server did not return a calendar. Please try again.');
    }
    downloadUrl = URL.createObjectURL(await response.blob());
    download.href = downloadUrl;
    download.download = `scarletcal-${payload.term}.ics`;
    download.hidden = false;
    const count = response.headers.get('X-Event-Count');
    const courses = response.headers.get('X-Course-Count');
    message(`Your calendar is ready: ${count} class events across ${courses} courses. Import the downloaded file into your calendar.`, 'success');
    download.click();
  } catch (error) {
    message(error.name === 'AbortError' ? 'The request timed out. Your text is still here—please try again.'
      : error instanceof TypeError ? 'Couldn’t reach the server. Your text is still here—check your connection and try again.'
      : error.message, 'error');
  } finally {
    fields.disabled = false;
    form.removeAttribute('aria-busy');
    generate.textContent = 'Generate calendar ↓';
  }
});
loadTerms();

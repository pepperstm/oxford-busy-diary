(() => {
  const results = document.getElementById('event-results');
  if (!results) return;

  const checks = [...results.querySelectorAll('.event-check')];
  const selectAll = document.getElementById('select-all');
  const apply = document.getElementById('bulk-apply');
  const count = document.getElementById('selected-count');
  const message = document.getElementById('review-message');
  let summaryRequest = 0;

  function visibleChecks() {
    return checks.filter(check => !check.closest('tr').hidden);
  }

  function updateSelection() {
    const visible = visibleChecks();
    const selected = visible.filter(check => check.checked);
    count.textContent = `${selected.length} selected`;
    apply.disabled = selected.length === 0;
    selectAll.checked = visible.length > 0 && selected.length === visible.length;
    selectAll.indeterminate = selected.length > 0 && selected.length < visible.length;
  }

  function setMessage(text, error = false) {
    message.textContent = text;
    message.classList.toggle('error', error);
    message.hidden = !text;
  }

  function updateVisibleRows() {
    const filter = results.dataset.statusFilter;
    results.querySelectorAll('tbody tr').forEach(row => {
      const status = row.querySelector('.review-form select').value;
      row.hidden = !!filter && status !== filter;
      if (row.hidden) row.querySelector('.event-check').checked = false;
    });
    updateSelection();
    let empty = results.querySelector('.review-empty');
    if (!empty) {
      empty = document.createElement('p');
      empty.className = 'review-empty';
      results.append(empty);
    }
    empty.hidden = visibleChecks().length !== 0;
    empty.textContent = 'No events remain with this review status. Change the Status filter to see them.';
  }

  async function refreshSummary() {
    const requestNumber = ++summaryRequest;
    try {
      const response = await fetch(window.location.href, { headers: { Accept: 'text/html' } });
      if (!response.ok) return;
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (requestNumber !== summaryRequest) return;
      const nextStats = page.getElementById('stats-section');
      if (nextStats) document.getElementById('stats-section').replaceWith(nextStats);
      const currentWatch = document.getElementById('watch-section');
      const nextWatch = page.getElementById('watch-section');
      if (currentWatch && nextWatch) currentWatch.replaceWith(nextWatch);
      else if (currentWatch && !nextWatch) currentWatch.remove();
      else if (!currentWatch && nextWatch) document.getElementById('stats-section').after(nextWatch);
    } catch (_) {
      // The review change has already been saved; summary cards can update on the next visit.
    }
  }

  async function postStatus(url, body) {
    const response = await fetch(url, { method: 'POST', headers: { Accept: 'application/json' }, body });
    if (!response.ok) throw new Error(`Could not save (${response.status}). Please try again.`);
    return response.json();
  }

  results.querySelectorAll('.review-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const select = form.querySelector('select');
      const previous = select.dataset.original;
      if (select.value === previous) return;
      select.disabled = true;
      setMessage('');
      try {
        const body = new FormData();
        body.set('status', select.value);
        await postStatus(form.action, body);
        select.dataset.original = select.value;
        updateVisibleRows();
        refreshSummary();
        setMessage('Review saved.');
      } catch (error) {
        select.value = previous;
        setMessage(error.message, true);
      } finally {
        select.disabled = false;
      }
    });
  });

  checks.forEach(check => check.addEventListener('change', updateSelection));
  selectAll.addEventListener('change', () => {
    visibleChecks().forEach(check => { check.checked = selectAll.checked; });
    updateSelection();
  });

  apply.addEventListener('click', async () => {
    const selected = visibleChecks().filter(check => check.checked);
    if (!selected.length) return;
    const status = document.getElementById('bulk-status').value;
    const body = new FormData();
    body.set('status', status);
    selected.forEach(check => body.append('event_ids', check.value));
    apply.disabled = true;
    setMessage('');
    try {
      const result = await postStatus('/events/bulk-status', body);
      selected.forEach(check => {
        const select = check.closest('tr').querySelector('.review-form select');
        select.value = status;
        select.dataset.original = status;
        check.checked = false;
      });
      updateVisibleRows();
      refreshSummary();
      setMessage(`${result.updated} event${result.updated === 1 ? '' : 's'} updated.`);
    } catch (error) {
      setMessage(error.message, true);
    } finally {
      updateSelection();
    }
  });
})();

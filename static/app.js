/* RepoTalk — Single-page application */

(function () {
  'use strict';

  // --- State ---
  let currentProjectId = null;
  let currentConvId = null;
  let streaming = false;

  // --- DOM refs ---
  const $ = (sel) => document.querySelector(sel);
  const projectSelect = $('#project-select');
  const convSelect = $('#conv-select');
  const messagesDiv = $('#messages');
  const chatInput = $('#chat-input');
  const btnSend = $('#btn-send');
  const statusText = $('#status-text');
  const indexProgress = $('#index-progress');
  const projectStats = $('#project-stats');

  // --- Helpers ---
  function setStatus(text) { statusText.textContent = text; }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API ${res.status}: ${err}`);
    }
    if (opts.raw) return res;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    return res.text();
  }

  // --- Projects ---
  async function loadProjects() {
    const projects = await api('/api/projects');
    projectSelect.innerHTML = '<option value="">Select a project...</option>';
    projects.forEach((p) => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.name} (${p.file_count || 0} files)`;
      projectSelect.appendChild(opt);
    });
    if (projects.length === 1) {
      projectSelect.value = projects[0].id;
      selectProject(projects[0].id);
    }
  }

  async function selectProject(id) {
    currentProjectId = id;
    currentConvId = null;
    if (!id) {
      projectStats.innerHTML = '';
      showWelcome();
      return;
    }
    // Load stats
    const projects = await api('/api/projects');
    const p = projects.find((x) => x.id === id);
    if (p) {
      projectStats.innerHTML = `
        <span class="stat"><span class="num">${p.file_count || 0}</span> files</span>
        <span class="stat"><span class="num">${p.graph_node_count || 0}</span> nodes</span>
        <span class="stat"><span class="num">${p.graph_edge_count || 0}</span> edges</span>
      `;
    }
    await loadConversations();
    showWelcome();
    setStatus(`Project: ${p?.name || id}`);
  }

  // --- New Project Modal ---
  $('#btn-new-project').addEventListener('click', () => {
    $('#modal-overlay').classList.remove('hidden');
    $('#np-name').focus();
  });
  $('#np-cancel').addEventListener('click', () => {
    $('#modal-overlay').classList.add('hidden');
  });
  $('#np-create').addEventListener('click', async () => {
    const name = $('#np-name').value.trim();
    const path = $('#np-path').value.trim();
    if (!name || !path) return;
    try {
      setStatus('Creating project...');
      const proj = await api('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name, source_path: path }),
      });
      $('#modal-overlay').classList.add('hidden');
      await loadProjects();
      projectSelect.value = proj.id;
      await selectProject(proj.id);
      // Trigger indexing
      setStatus('Indexing started...');
      await api(`/api/projects/${proj.id}/index`, { method: 'POST' });
      pollIndexStatus(proj.id);
    } catch (e) {
      alert('Error: ' + e.message);
      setStatus('Error creating project');
    }
  });

  function pollIndexStatus(projectId) {
    indexProgress.classList.remove('hidden');
    const poll = setInterval(async () => {
      try {
        const s = await api(`/api/projects/${projectId}/index-status`);
        indexProgress.textContent = `${s.phase || s.status}: ${s.files_done || 0}/${s.files_total || '?'} — ${s.message || ''}`;
        if (s.status === 'completed' || s.status === 'idle' || s.status === 'failed') {
          clearInterval(poll);
          indexProgress.classList.add('hidden');
          setStatus(s.status === 'completed' ? 'Indexing complete' : `Indexing: ${s.status}`);
          await loadProjects();
          projectSelect.value = projectId;
          await selectProject(projectId);
        }
      } catch {
        clearInterval(poll);
        indexProgress.classList.add('hidden');
      }
    }, 2000);
  }

  // --- Conversations ---
  async function loadConversations() {
    if (!currentProjectId) return;
    const convs = await api(`/api/projects/${currentProjectId}/conversations`);
    convSelect.innerHTML = '<option value="">New conversation</option>';
    convs.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.title || 'Untitled';
      convSelect.appendChild(opt);
    });
  }

  convSelect.addEventListener('change', async () => {
    const id = convSelect.value;
    if (id) {
      currentConvId = id;
      await loadMessages(id);
    } else {
      currentConvId = null;
      showWelcome();
    }
  });

  async function loadMessages(convId) {
    const msgs = await api(`/api/conversations/${convId}/messages`);
    messagesDiv.innerHTML = '';
    msgs.forEach((m) => {
      appendMessage(m.role, m.content, m.references);
    });
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // --- Welcome ---
  function showWelcome() {
    messagesDiv.innerHTML = '';
    const sampleQuestions = [
      'What does this project do?',
      'Show me the main entry points',
      'How is authentication implemented?',
      'What are the key data models?',
    ];
    const div = document.createElement('div');
    div.className = 'welcome';
    div.innerHTML = `
      <h2>Welcome to RepoTalk</h2>
      <p>Ask questions about your codebase</p>
      <div class="sample-questions">
        ${sampleQuestions.map((q) => `<button class="sample-q">${q}</button>`).join('')}
      </div>
    `;
    messagesDiv.appendChild(div);
    div.querySelectorAll('.sample-q').forEach((btn) => {
      btn.addEventListener('click', () => {
        chatInput.value = btn.textContent;
        sendMessage();
      });
    });
  }

  // --- Chat ---
  function appendMessage(role, content, references) {
    // Remove welcome if present
    const welcome = messagesDiv.querySelector('.welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = `msg msg-${role}`;
    if (role === 'assistant') {
      div.innerHTML = marked.parse(content || '');
      // Highlight code blocks
      div.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
    } else {
      div.textContent = content;
    }

    // References
    if (references && references.length > 0) {
      const refsDiv = document.createElement('div');
      refsDiv.className = 'references';
      const seen = new Set();
      references.forEach((ref) => {
        const source = typeof ref === 'string' ? ref : ref.source || ref.path || '';
        if (!source || seen.has(source)) return;
        seen.add(source);
        const chip = document.createElement('span');
        chip.className = 'ref-chip';
        chip.textContent = source.split('/').slice(-2).join('/');
        chip.title = source;
        chip.addEventListener('click', () => openSourceFile(source));
        refsDiv.appendChild(chip);
      });
      div.appendChild(refsDiv);
    }

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return div;
  }

  async function sendMessage() {
    if (streaming || !currentProjectId) return;
    const content = chatInput.value.trim();
    if (!content) return;

    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Create conversation if needed
    if (!currentConvId) {
      try {
        const conv = await api(`/api/projects/${currentProjectId}/conversations`, {
          method: 'POST',
          body: JSON.stringify({ title: content.slice(0, 60) }),
        });
        currentConvId = conv.id;
        await loadConversations();
        convSelect.value = conv.id;
      } catch (e) {
        setStatus('Error: ' + e.message);
        return;
      }
    }

    appendMessage('user', content);

    // Create streaming assistant message
    const assistantDiv = appendMessage('assistant', '');
    streaming = true;
    btnSend.disabled = true;
    setStatus('Streaming response...');

    const collectedRefs = [];
    const collectedSuggestions = [];
    let collectedContent = '';

    try {
      const res = await fetch(`/api/conversations/${currentConvId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`API ${res.status}: ${errText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double newlines to get complete event blocks
        const blocks = buffer.split('\n\n');
        // Last element may be incomplete — keep it in buffer
        buffer = blocks.pop();

        for (const block of blocks) {
          if (!block.trim()) continue;

          // Parse event type and data from block
          let eventType = '';
          let dataStr = '';
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              dataStr = line.slice(5).trim();
            }
          }

          if (!dataStr) continue;

          let data;
          try {
            data = JSON.parse(dataStr);
          } catch {
            continue;
          }

          switch (eventType) {
            case 'token':
              collectedContent += data.content || '';
              assistantDiv.innerHTML = marked.parse(collectedContent);
              assistantDiv.querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
              messagesDiv.scrollTop = messagesDiv.scrollHeight;
              break;

            case 'reference':
              collectedRefs.push(data);
              break;

            case 'context_used':
              // Optional: could display context info
              break;

            case 'suggestions':
              if (data.suggestions) collectedSuggestions.push(...data.suggestions);
              break;

            case 'done':
              break;
          }
        }
      }

      // Append references after streaming completes
      if (collectedRefs.length > 0) {
        const refsDiv = document.createElement('div');
        refsDiv.className = 'references';
        collectedRefs.forEach((ref) => {
          const chip = document.createElement('span');
          chip.className = 'ref-chip';
          const source = ref.source || '';
          chip.textContent = source.split('/').slice(-2).join('/');
          chip.title = source;
          chip.addEventListener('click', () => openSourceFile(source));
          refsDiv.appendChild(chip);
        });
        assistantDiv.appendChild(refsDiv);
      }

      // Append suggestions
      if (collectedSuggestions.length > 0) {
        const sugDiv = document.createElement('div');
        sugDiv.className = 'suggestions';
        collectedSuggestions.forEach((s) => {
          const chip = document.createElement('span');
          chip.className = 'suggestion-chip';
          chip.textContent = s;
          chip.addEventListener('click', () => {
            chatInput.value = s;
            sendMessage();
          });
          sugDiv.appendChild(chip);
        });
        assistantDiv.appendChild(sugDiv);
      }

    } catch (e) {
      assistantDiv.innerHTML = `<span style="color:var(--accent-red)">Error: ${e.message}</span>`;
    }

    streaming = false;
    btnSend.disabled = false;
    setStatus('Ready');
  }

  btnSend.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  projectSelect.addEventListener('change', () => selectProject(projectSelect.value));

  // --- Source Tab ---
  async function openSourceFile(path) {
    if (!currentProjectId) return;
    // Switch to source tab
    activateTab('source');

    $('#source-header').textContent = path;
    $('#source-code').textContent = 'Loading...';
    $('#source-code').className = 'hljs';

    try {
      // Find the file ID from the files list
      const files = await api(`/api/projects/${currentProjectId}/files`);
      // Strip .md suffix from doc reference paths to match source file paths
      const cleanPath = path.replace(/\.md$/, '');
      const file = files.find((f) => 
        f.relative_path === path || 
        f.relative_path === cleanPath ||
        cleanPath.endsWith(f.relative_path) || 
        f.relative_path.endsWith(cleanPath) ||
        path.endsWith(f.relative_path)
      );
      if (!file) {
        $('#source-code').textContent = `File not found: ${path}`;
        return;
      }
      const src = await api(`/api/projects/${currentProjectId}/files/${file.id}/source`);
      const code = $('#source-code');
      code.textContent = src.content || src;
      if (src.language) {
        code.className = `hljs language-${src.language}`;
      }
      hljs.highlightElement(code);
    } catch (e) {
      $('#source-code').textContent = `Error loading file: ${e.message}`;
    }
  }

  // --- Tabs ---
  function activateTab(name) {
    document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.tab-content').forEach((t) => t.classList.toggle('active', t.id === `tab-${name}`));
  }

  document.querySelectorAll('.tab').forEach((t) => {
    t.addEventListener('click', () => activateTab(t.dataset.tab));
  });

  // --- Graph Tab ---
  let cyInstance = null;

  $('#btn-load-graph').addEventListener('click', loadGraph);

  async function loadGraph() {
    if (!currentProjectId) return;
    $('#graph-info').textContent = 'Loading...';
    setStatus('Loading graph data...');

    try {
      const data = await api(`/api/projects/${currentProjectId}/graph`);
      const nodes = data.nodes || [];
      const edges = data.edges || [];

      // Sample nodes if too many
      const MAX_NODES = 500;
      let sampledNodes = nodes;
      let sampledEdges = edges;
      if (nodes.length > MAX_NODES) {
        // Keep nodes with most connections
        const connectionCount = {};
        edges.forEach((e) => {
          connectionCount[e.source_node_id] = (connectionCount[e.source_node_id] || 0) + 1;
          connectionCount[e.target_node_id] = (connectionCount[e.target_node_id] || 0) + 1;
        });
        sampledNodes = [...nodes]
          .sort((a, b) => (connectionCount[b.id] || 0) - (connectionCount[a.id] || 0))
          .slice(0, MAX_NODES);
        const nodeIds = new Set(sampledNodes.map((n) => n.id));
        sampledEdges = edges.filter((e) => nodeIds.has(e.source_node_id) && nodeIds.has(e.target_node_id));
      }

      const nodeColors = {
        file: '#60a5fa',
        module: '#8b5cf6',
        class: '#f59e0b',
        function: '#34d399',
        method: '#34d399',
        variable: '#f87171',
        import: '#94a3b8',
      };

      const cyNodes = sampledNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.display_name || n.qualified_name || n.id,
          type: n.node_type,
          color: nodeColors[n.node_type] || '#8b5cf6',
          qualified_name: n.qualified_name,
          complexity: n.complexity,
          line_start: n.line_start,
          line_end: n.line_end,
        },
      }));

      const cyEdges = sampledEdges.map((e) => ({
        data: {
          source: e.source_node_id,
          target: e.target_node_id,
          type: e.edge_type,
        },
      }));

      if (cyInstance) cyInstance.destroy();

      cyInstance = cytoscape({
        container: $('#cy'),
        elements: { nodes: cyNodes, edges: cyEdges },
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              label: 'data(label)',
              color: '#e2e8f0',
              'font-size': '8px',
              'text-valign': 'bottom',
              'text-margin-y': 4,
              width: 12,
              height: 12,
              'text-max-width': '80px',
              'text-wrap': 'ellipsis',
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1,
              'line-color': '#334155',
              'target-arrow-color': '#334155',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.6,
            },
          },
        ],
        layout: {
          name: 'cose',
          animate: false,
          nodeOverlap: 20,
          idealEdgeLength: 80,
          nodeRepulsion: 8000,
          numIter: 200,
        },
        minZoom: 0.1,
        maxZoom: 5,
      });

      // Node click — show info tooltip
      let nodeInfoEl = null;
      cyInstance.on('tap', 'node', (evt) => {
        const d = evt.target.data();
        if (nodeInfoEl) nodeInfoEl.remove();
        nodeInfoEl = document.createElement('div');
        nodeInfoEl.className = 'node-info';
        nodeInfoEl.innerHTML = `
          <div class="label">${d.label}</div>
          <div class="detail">Type: ${d.type}</div>
          ${d.qualified_name ? `<div class="detail">Name: ${d.qualified_name}</div>` : ''}
          ${d.complexity ? `<div class="detail">Complexity: ${d.complexity}</div>` : ''}
          ${d.line_start ? `<div class="detail">Lines: ${d.line_start}–${d.line_end || '?'}</div>` : ''}
        `;
        const pos = evt.renderedPosition;
        const container = $('#cy').getBoundingClientRect();
        nodeInfoEl.style.left = (container.left + pos.x + 15) + 'px';
        nodeInfoEl.style.top = (container.top + pos.y - 10) + 'px';
        document.body.appendChild(nodeInfoEl);
        setTimeout(() => { if (nodeInfoEl) nodeInfoEl.remove(); }, 3000);
      });

      cyInstance.on('tap', (evt) => {
        if (evt.target === cyInstance && nodeInfoEl) {
          nodeInfoEl.remove();
          nodeInfoEl = null;
        }
      });

      $('#graph-info').textContent = `${sampledNodes.length} nodes, ${sampledEdges.length} edges${nodes.length > MAX_NODES ? ` (sampled from ${nodes.length})` : ''}`;
      setStatus('Graph loaded');
    } catch (e) {
      $('#graph-info').textContent = `Error: ${e.message}`;
      setStatus('Error loading graph');
    }
  }

  // --- Docs Tab ---
  async function loadDocsTree() {
    if (!currentProjectId) return;
    try {
      const tree = await api(`/api/projects/${currentProjectId}/docs/tree`);
      const container = $('#docs-tree');
      container.innerHTML = '';
      renderTree(container, tree);
    } catch {
      $('#docs-tree').innerHTML = '<div style="padding:8px;color:var(--text-dim)">No docs available</div>';
    }
  }

  function renderTree(container, items) {
    if (!items || !items.length) return;
    items.forEach((item) => {
      if (item.type === 'directory') {
        const dir = document.createElement('div');
        dir.className = 'tree-dir';
        dir.textContent = item.name;
        container.appendChild(dir);

        const children = document.createElement('div');
        children.className = 'tree-children collapsed';
        container.appendChild(children);

        dir.addEventListener('click', () => {
          dir.classList.toggle('open');
          children.classList.toggle('collapsed');
        });

        renderTree(children, item.children);
      } else {
        const file = document.createElement('div');
        file.className = 'tree-file' + (item.has_doc ? ' has-doc' : '');
        file.textContent = item.name;
        file.addEventListener('click', () => loadDoc(item.path));
        container.appendChild(file);
      }
    });
  }

  async function loadDoc(path) {
    try {
      const content = await api(`/api/projects/${currentProjectId}/docs/${encodeURIComponent(path)}`);
      const html = marked.parse(typeof content === 'string' ? content : content.content || JSON.stringify(content));
      $('#docs-content').innerHTML = html;
      $('#docs-content').querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
    } catch (e) {
      $('#docs-content').innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
  }

  // --- Init ---
  async function init() {
    await loadProjects();
    showWelcome();
  }

  // Reload docs tree when switching to docs tab or changing project
  document.querySelector('[data-tab="docs"]').addEventListener('click', loadDocsTree);

  init().catch((e) => setStatus('Error: ' + e.message));
})();

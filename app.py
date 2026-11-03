import streamlit as st
import tempfile
import os
import uuid
import time

_start = time.time()

from db.sessions import init_db, save_session, load_session, delete_session
from retrieval.scope_detect import detect_sources
print(f"init_db done: {time.time() - _start:.2f}s")


# ── Cached imports — only load once per session ──────────
@st.cache_resource(show_spinner=False)
def load_pipeline():
    from pipeline import ask, format_response
    return ask, format_response

@st.cache_resource(show_spinner=False)
def load_ingest():
    from ingestion import ingest
    return ingest

@st.cache_resource(show_spinner=False)
def load_memory():
    from generation.memory import create_memory
    return create_memory

with st.spinner('Starting DocSense...'):
    ask, format_response = load_pipeline()
    ingest = load_ingest()
    create_memory = load_memory()

print(f"imports done: {time.time() - _start:.2f}s")

# Initialise the database on app startup
init_db()
print(f"init_db done: {time.time() - _start:.2f}s")

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title='DocSense',
    page_icon='📄',
    layout='wide'
)

# ── Font ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"],
h1, h2, h3, h4, h5, h6, p, label,
button, input, textarea {
    font-family: 'Poppins', sans-serif !important;
}

body, [class*="css"],
p, label, button, input, textarea {
    font-size: 13px !important;
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    font-size: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ─────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'ingested_files' not in st.session_state:
    st.session_state.ingested_files = []
if 'doc_sources' not in st.session_state:
    st.session_state.doc_sources = {}   # display name -> full `source` metadata value
if 'upload_bytes' not in st.session_state:
    st.session_state.upload_bytes = {}  # uploaded filename -> PDF bytes (for the in-app viewer)
if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False
if 'memory' not in st.session_state:
    st.session_state.memory = create_memory()
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    stored = load_session(st.session_state.session_id)
    if stored:
        st.session_state.messages = stored

print(f"session state done: {time.time() - _start:.2f}s")

# ── Helpers ──────────────────────────────────────────────
def confidence_badge(level: str) -> str:
    badges = {
        'high':   '🟢 High confidence',
        'medium': '🟡 Medium confidence',
        'low':    '🔴 Low confidence — treat with caution',
    }
    return badges.get(level, '⚪ Unknown')

# Display metadata for files in demo_corpus/ (filename -> card info).
# A PDF dropped into demo_corpus/ without an entry here still works, just with a plain card.
DEMO_DOCS = {
    'The Honey Bee Apis mellifera - An Insect at the Interface between Human and Ecosystem Health.pdf': {
        'title': 'The Honey Bee Apis mellifera: An Insect at the Interface between Human and Ecosystem Health',
        'byline': 'Papa, G. et al. · Biology (MDPI), 2022 · 24 pages',
        'license': 'Open access, CC BY 4.0 · doi.org/10.3390/biology11020233',
    },
}

@st.cache_data(show_spinner=False)
def read_pdf_bytes(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()

def get_pdf_bytes(name: str) -> bytes | None:
    """PDF bytes for any document in this session: demo files from disk, uploads from session state."""
    if name in st.session_state.upload_bytes:
        return st.session_state.upload_bytes[name]
    path = os.path.join('demo_corpus', name)
    return read_pdf_bytes(path) if os.path.exists(path) else None

@st.dialog('📄 Document viewer', width='large')
def show_pdf(name: str):
    st.caption(DEMO_DOCS.get(name, {}).get('title', name))
    data = get_pdf_bytes(name)
    if data is None:
        st.error('This document is no longer available to view.')
        return
    st.pdf(data, height=720)

# ── Page header ──────────────────────────────────────────
st.title('📄 DocSense')
st.caption('Intelligent document Q&A with source grounding')

col_chat, col_citations = st.columns([2, 1])

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.header('📁 Documents')

    print(f"sidebar done: {time.time() - _start:.2f}s")

    # ── Demo document ─────────────────────────────────
    st.caption('Try it with a demo paper — open it to see what you can ask about:')
    demo_files = sorted(f for f in os.listdir('demo_corpus') if f.endswith('.pdf'))
    for i, demo_file in enumerate(demo_files):
        meta = DEMO_DOCS.get(demo_file, {})
        with st.container(border=True):
            st.markdown(f"**{meta.get('title', demo_file)}**")
            if meta.get('byline'):
                st.caption(meta['byline'])
            if meta.get('license'):
                st.caption(meta['license'])
            b_open, b_dl = st.columns(2)
            if b_open.button('Open', key=f'open_demo_{i}', use_container_width=True):
                show_pdf(demo_file)
            b_dl.download_button(
                'Download', data=get_pdf_bytes(demo_file), file_name=demo_file,
                mime='application/pdf', key=f'dl_demo_{i}', use_container_width=True
            )

    all_loaded = all(f in st.session_state.ingested_files for f in demo_files)
    if st.button('✅ Demo loaded' if all_loaded else '▶  Load demo into DocSense',
                 use_container_width=True, disabled=all_loaded or not demo_files):
        for demo_file in demo_files:
            path = os.path.join('demo_corpus', demo_file)
            if demo_file not in st.session_state.ingested_files:
                with st.spinner('Loading demo paper...'):
                    ingest(path, source_name=f"demo_corpus/{demo_file}")
                    st.session_state.ingested_files.append(demo_file)
                    st.session_state.doc_sources[demo_file] = f"demo_corpus/{demo_file}"
        st.session_state.demo_mode = True
        st.rerun()

    st.divider()

    # ── File uploader ─────────────────────────────────
    uploaded_files = st.file_uploader(
        'Upload your own PDFs',
        type='pdf',
        accept_multiple_files=True
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.ingested_files:
                pdf_bytes = uploaded_file.getvalue()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                with st.spinner(f'Processing {uploaded_file.name}...'):
                    n = ingest(tmp_path, source_name=f"uploads/{uploaded_file.name}")
                os.unlink(tmp_path)
                st.session_state.ingested_files.append(uploaded_file.name)
                st.session_state.doc_sources[uploaded_file.name] = f"uploads/{uploaded_file.name}"
                st.session_state.upload_bytes[uploaded_file.name] = pdf_bytes
                st.success(f'✅ {uploaded_file.name} — {n} chunks indexed')

    # ── Ingested files list (each openable in the viewer) ──
    if st.session_state.ingested_files:
        st.divider()
        st.caption('Indexed documents:')
        for i, fname in enumerate(st.session_state.ingested_files):
            name_col, open_col = st.columns([4, 1])
            name_col.markdown(f"• {DEMO_DOCS.get(fname, {}).get('title', fname)}")
            if open_col.button('👁', key=f'open_indexed_{i}', help='Open in viewer'):
                show_pdf(fname)

    # ── Document scope ────────────────────────────────
    doc_scope = []
    if st.session_state.ingested_files:
        st.divider()
        doc_scope = st.multiselect(
            'Search scope',
            options=st.session_state.ingested_files,
            help='Restrict retrieval to one or more documents. Leave empty to search all documents loaded in this session.'
        )
        scope_key = tuple(sorted(doc_scope))
        if 'last_doc_scope' not in st.session_state:
            st.session_state.last_doc_scope = scope_key
        if scope_key != st.session_state.last_doc_scope:
            # Switching scope is a topic change — stale conversation memory would
            # otherwise get carried into query rewriting for the new document(s)/pool.
            st.session_state.memory = create_memory()
            st.session_state.last_doc_scope = scope_key

    # ── Retrieval settings ────────────────────────────
    st.divider()
    st.caption('Retrieval settings')
    rerank_enabled = st.toggle(
        'Enable re-ranking (Cohere)',
        value=True,
        help='Two-stage retrieval: similarity search → Cohere Rerank. Higher quality, one extra API call per query.'
    )

    # ── Clear conversation ────────────────────────────
    st.divider()
    if st.button('🗑  Clear conversation', use_container_width=True):
        delete_session(st.session_state.session_id)
        st.session_state.messages = []
        st.session_state.memory = create_memory()
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# ── Chat column ──────────────────────────────────────────
with col_chat:
    st.subheader('💬 Ask a question')

    if not st.session_state.ingested_files:
        st.info('👈 Load the demo paper (open it first to see what it covers) or upload your own PDF to get started.')
    else:
        # ── Conversation history ──────────────────────
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
                if msg['role'] == 'assistant' and 'confidence' in msg:
                    st.caption(confidence_badge(msg['confidence']))
                    mode_label = '🔄 Re-ranked' if msg.get('rerank_enabled') else '🔍 Similarity only'
                    st.caption(mode_label)
                    if msg.get('auto_scope'):
                        st.caption(f"🎯 Auto-scoped to: {', '.join(msg['auto_scope'])}")

        # ── Context length warning ────────────────────
        if len(st.session_state.messages) > 16:
            st.warning(
                '⚠️ This conversation is getting long. Answer quality may reduce. '
                'Consider clearing the conversation and starting fresh.',
                icon='⚠️'
            )

        # ── Chat input ────────────────────────────────
        if prompt := st.chat_input('Ask something about your documents...'):
            st.session_state.messages.append({'role': 'user', 'content': prompt})
            with st.chat_message('user'):
                st.markdown(prompt)

            with st.chat_message('assistant'):
                with st.spinner('Searching documents...'):
                    try:
                        # Picker wins; if it's empty, infer scope from documents
                        # named in the question itself (retrieval/scope_detect.py).
                        auto_scope = []
                        if doc_scope:
                            source_filter = [st.session_state.doc_sources[name] for name in doc_scope]
                        else:
                            auto_scope = detect_sources(prompt, st.session_state.doc_sources)
                            # Never search the whole shared index: on a public deployment it
                            # holds other visitors' uploads. "All" = all docs in THIS session.
                            source_filter = auto_scope or list(st.session_state.doc_sources.values())
                        result = ask(
                            prompt,
                            rerank_enabled=rerank_enabled,
                            memory=st.session_state.memory,
                            source_filter=source_filter
                        )
                    except Exception as e:
                        auto_scope = []
                        result = {
                            'answer': 'Something went wrong while generating the answer. Please try again.',
                            'sources': [],
                            'confidence': 'low',
                            'rerank_enabled': rerank_enabled
                        }
                        st.error(f'Error: {str(e)}')
                st.markdown(result['answer'])
                st.caption(confidence_badge(result['confidence']))
                mode_label = '🔄 Re-ranked' if result.get('rerank_enabled') else '🔍 Similarity only'
                st.caption(mode_label)

            st.session_state.messages.append({
                'role': 'assistant',
                'content': result['answer'],
                'confidence': result['confidence'],
                'sources': result['sources'],
                'rerank_enabled': result.get('rerank_enabled'),
                'auto_scope': [s.split('/')[-1] for s in auto_scope]
            })
            save_session(st.session_state.session_id, st.session_state.messages)
            st.rerun()

# ── Citations column ─────────────────────────────────────
with col_citations:
    st.subheader('📎 Sources')

    last_sources = []
    for msg in reversed(st.session_state.messages):
        if msg['role'] == 'assistant' and msg.get('sources'):
            last_sources = msg['sources']
            break

    if not last_sources:
        st.caption('Citations will appear here alongside each answer.')
    else:
        seen = set()
        for s in last_sources:
            source = s['source'].replace('\\', '/')
            if 'Temp' in source or 'tmp' in source.lower():
                continue
            key = f"{source} — Page {s['page']}"
            if key not in seen:
                seen.add(key)
                with st.expander(f"📄 Page {s['page']}", expanded=True):
                    st.caption(source)
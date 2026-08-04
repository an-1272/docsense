import streamlit as st
from pipeline import ask
from ingestion import ingest
import tempfile
import os

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title='DocSense',
    page_icon='📄',
    layout='wide'
)

# ── Session state initialisation ─────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'ingested_files' not in st.session_state:
    st.session_state.ingested_files = []
if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

# ── Layout ───────────────────────────────────────────────
st.title('📄 DocSense')
st.caption('Intelligent document Q&A with source grounding')

col_chat, col_citations = st.columns([2, 1])

with col_chat:
    st.subheader('Ask a question')
    st.info('Upload a document in the sidebar to get started.')

with col_citations:
    st.subheader('Sources')
    st.caption('Citations will appear here alongside each answer.')

# ── Sidebar placeholder ──────────────────────────────────
with st.sidebar:
    st.header('Documents')
    st.caption('Upload PDFs to query against.')
with st.sidebar:
    st.header('📁 Documents')

    # ── Demo mode toggle ──────────────────────────────
    if st.button('▶  Load Demo Documents', use_container_width=True):
        demo_files = [f for f in os.listdir('demo_corpus') if f.endswith('.pdf')]
        for demo_file in demo_files:
            path = os.path.join('demo_corpus', demo_file)
            if demo_file not in st.session_state.ingested_files:
                with st.spinner(f'Loading {demo_file}...'):
                    ingest(path)
                    st.session_state.ingested_files.append(demo_file)
        st.session_state.demo_mode = True
        st.success(f'Loaded {len(demo_files)} demo document(s)')

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
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                with st.spinner(f'Processing {uploaded_file.name}...'):
                    n = ingest(tmp_path)
                os.unlink(tmp_path)
                st.session_state.ingested_files.append(uploaded_file.name)
                st.success(f'✅ {uploaded_file.name} — {n} chunks indexed')

# ── Ingested files list ───────────────────────────
    if st.session_state.ingested_files:
        st.divider()
        st.caption('Indexed documents:')
        for fname in st.session_state.ingested_files:
            st.markdown(f'• {fname}')

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
        st.session_state.messages = []
        st.rerun()

    
# ── Helpers ──────────────────────────────────────────────
def confidence_badge(level: str) -> str:
    badges = {
        'high':   '🟢 High confidence',
        'medium': '🟡 Medium confidence',
        'low':    '🔴 Low confidence — treat with caution',
    }
    return badges.get(level, '⚪ Unknown')
with col_chat:
    st.subheader('💬 Ask a question')

    # ── Guard: require documents first ───────────────
    if not st.session_state.ingested_files:
        st.info('👈 Upload a document or load the demo to get started.')
    else:
        # ── Display conversation history ──────────────
        for msg in st.session_state.messages:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
                if msg['role'] == 'assistant' and 'confidence' in msg:
                    st.caption(confidence_badge(msg['confidence']))
        
        # Context length warning
        if len(st.session_state.messages) > 16:
            st.warning(
                '⚠️ This conversation is getting long. Answer quality may reduce. '
                'Consider clearing the conversation and starting fresh.',
                icon='⚠️'
            )

        # ── Chat input ────────────────────────────────
        if prompt := st.chat_input('Ask something about your documents...'):
            # Show user message
            st.session_state.messages.append({'role': 'user', 'content': prompt})
            with st.chat_message('user'):
                st.markdown(prompt)

            # Get answer
            with st.chat_message('assistant'):
                with st.spinner('Searching documents...'):
                    try:
                        result = ask(prompt, rerank_enabled=rerank_enabled)
                    except Exception as e:
                        result = {
                            'answer': f'Something went wrong while generating the answer. Please try again.',
                            'sources': [],
                            'confidence': 'low'
                        }
                        st.error(f'Error: {str(e)}')
                st.markdown(result['answer'])
                st.caption(confidence_badge(result['confidence']))
                mode_label = '🔄 Re-ranked' if result.get('rerank_enabled') else '🔍 Similarity only'
                st.caption(mode_label)



            # Store in history
            st.session_state.messages.append({
                'role': 'assistant',
                'content': result['answer'],
                'confidence': result['confidence'],
                'sources': result['sources']
            })
            st.rerun()
with col_citations:
    st.subheader('📎 Sources')

    # Show sources from the most recent assistant message
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
            key = f"{s['source']} — Page {s['page']}"
            if key not in seen:
                seen.add(key)
                with st.expander(f"📄 Page {s['page']}", expanded=True):
                    st.caption(s['source'])

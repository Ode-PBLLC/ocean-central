<p align="left">
  <img src="Assets/OC Logo lockup.png" alt="Ocean Central Logo" width="300">
</p>

# What is Ocean Central?

It is a collaborative platform designed to track and advance ocean regeneration using the best available open-source data. The platform tracks progress across six key areas where reducing pressures on the ocean can support its regeneration by 2050:

---

### **Protect Marine Life:** 
Safeguarding marine species is critical for biodiversity, climate regulation, and human well-being.  
[Link to Notebook](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/marine_life_FINAL.ipynb)

---

### **Protect Spaces:** 
Marine protection preserves essential ecosystems, fostering long-term ocean health.  
[[Link to Notebook]](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/protect_spaces_FINAL.ipynb)

---

### **Restore Ecosystems:** 
Restoring habitats boosts biodiversity, coastal defense, and carbon storage.  
[[Link to Notebook]](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/restore_ecosystems_FINAL.ipynb)

---

### **Harvest Wisely:** 
Ensuring sustainable use of marine resources protects future generations and ecosystem health.  
[Link to Notebook](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/harvest_wisely_FINAL.ipynb)

---

### **Reduce Pollution:** 
Decreasing pollution supports biodiversity, clean water, and sustainable fisheries.  
[Link to Notebook](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/reduce_pollution_FINAL.ipynb)

---

### **Mitigate Climate Change:**
Limiting climate impacts is essential for maintaining the ocean's role in climate regulation.
[Link to Notebook](https://github.com/Ode-PBLLC/ocean-central/blob/main/Code/mitigate_climate_change_FINAL.ipynb)

---

## Ocean Central AI Assistant

Ocean Central includes an AI-powered query system that provides accessible, scientifically-grounded answers to marine science and oceanography questions.

### Features:

- **Hybrid Knowledge System**: Combines retrieval-augmented generation (RAG) from authoritative sources with real-time web search for comprehensive, up-to-date answers
- **Authoritative Sources**:
  - Ocean Studies - Introduction to Oceanography (Segar et al., 2018)
  - IPCC reports
  - Carlos Duarte scientific papers
  - Ocean Central platform content
- **Accessible Language**: Responses are tailored to be understandable by a broad audience while maintaining scientific accuracy
- **Source Verification**: Web search results are reviewed to ensure only reputable sources (peer-reviewed articles, government institutions, academic publishers, established news organizations) are cited
- **Smart Caching**: Efficient caching system that refreshes web search results daily while maintaining stable answers from document sources
- **Citation Support**: All answers include proper citations with snippet references and source attribution

### How It Works:

1. **Multi-Source Search**: Queries are simultaneously searched across Ocean Central content, oceanography textbooks, IPCC reports, and Duarte papers
2. **RAG Response**: Initial answer generated from retrieved document snippets
3. **Web Enhancement**: Real-time web search supplements the RAG response with current information
4. **Response Consolidation**: Both sources are intelligently combined into a single, coherent answer with proper citations
5. **Quality Control**: Web sources are vetted to exclude unreliable content

The AI assistant is available through the `/query` API endpoint and is designed to support researchers, educators, and ocean advocates with reliable marine science information.

import os
import re

dirs = ['d:/GITHUB/MyStreamlitApp/ERP_Sim_Integrated', 'd:/GITHUB/MyStreamlitApp/ERP_Sim_Integrated/pages']

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # We want to replace st.markdown(..., unsafe_allow_html=True) with st.html(...)
    # only for block tags: <div, <style.
    # We can do this using a regex because the calls are strictly formatted.

    # Fix multi-line string markdown blocks
    content = re.sub(
        r'st\.markdown\(\s*(f?"""\n?\s*<div.*?"""),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r'st\.markdown\(\s*(f?\'\'\'\n?\s*<div.*?\'\'\'),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'st\.markdown\(\s*(f?"""\n?\s*<style.*?"""),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'st\.markdown\(\s*(f?\'\'\'\n?\s*<style.*?\'\'\'),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content,
        flags=re.DOTALL
    )

    # single line
    content = re.sub(
        r'st\.markdown\((f?"<div.*?</div>"),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content
    )
    
    content = re.sub(
        r'st\.markdown\((f?\'<div.*?</div>\'),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content
    )
    
    content = re.sub(
        r'st\.markdown\((f?"<hr.*?>"),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content
    )

    content = re.sub(
        r'st\.markdown\((f?\'<hr.*?>\'),\s*unsafe_allow_html=True\)',
        r'st.html(\1)',
        content
    )

    # In 07_inbox.py, the multi-line string is passed without """
    # st.html(f"<div... f"..." f"</div>")
    # We can just match st.markdown( ... unsafe_allow_html=True ) and swap it
    # if it doesn't contain ** or _.
    # Let's write a generic replacer for 07_inbox.
    if 'pages' in filepath and '07_inbox.py' in filepath:
        content = re.sub(
            r'st\.markdown\(\s*(f?"<div class=\'inbox-card.*?</div>",)\s*unsafe_allow_html=True\s*\)',
            r'st.html(\1)',
            content,
            flags=re.DOTALL
        )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for d in dirs:
    for f in os.listdir(d):
        if f.endswith('.py'):
            patch_file(os.path.join(d, f))

print('Patch applied successfully')

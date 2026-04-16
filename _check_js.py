import sys
src=open('static/app.js','r',encoding='utf-8').read()
pairs={'{':'}','[':']','(':')'}
stack=[]
in_str=None
esc=False
line=1
col=0
in_single_comment=False
in_block_comment=False
i=0
BACKSLASH=chr(92)
while i<len(src):
    c=src[i]
    if c=='\n':
        line+=1; col=0
        if in_single_comment: in_single_comment=False
    else:
        col+=1
    if in_single_comment:
        i+=1; continue
    if in_block_comment:
        if c=='*' and i+1<len(src) and src[i+1]=='/':
            in_block_comment=False; i+=2; continue
        i+=1; continue
    if in_str is not None:
        if esc:
            esc=False
        elif c==BACKSLASH:
            esc=True
        elif c==in_str:
            in_str=None
        i+=1; continue
    if c=='"' or c=="'" or c=='`':
        in_str=c; i+=1; continue
    if c=='/' and i+1<len(src):
        if src[i+1]=='/':
            in_single_comment=True; i+=2; continue
        if src[i+1]=='*':
            in_block_comment=True; i+=2; continue
    if c in '{[(':
        stack.append((c,line,col))
    elif c in '}])':
        if not stack:
            print(f'EXTRA {c} at {line}:{col}'); sys.exit(1)
        o,ol,oc=stack.pop()
        if pairs[o]!=c:
            print(f'MISMATCH: opened {o!r} at {ol}:{oc} closed {c!r} at {line}:{col}'); sys.exit(1)
    i+=1
if stack:
    print('UNCLOSED:',stack[-5:])
else:
    print('BALANCED')

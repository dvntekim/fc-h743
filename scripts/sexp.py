# Minimal S-expression parser/writer for KiCad files
import re
class Sym(str): pass
def tokenize(s):
    i=0; n=len(s)
    while i<n:
        c=s[i]
        if c in ' \t\r\n': i+=1; continue
        if c=='(' or c==')': yield c; i+=1; continue
        if c=='"':
            j=i+1; buf=[]
            while s[j]!='"':
                if s[j]=='\\': buf.append(s[j+1]); j+=2; continue
                buf.append(s[j]); j+=1
            yield ('str',''.join(buf)); i=j+1; continue
        j=i
        while j<n and s[j] not in ' \t\r\n()': j+=1
        yield Sym(s[i:j]); i=j
def parse(s):
    stack=[[]]
    for t in tokenize(s):
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        elif isinstance(t,tuple): stack[-1].append(t[1])
        else: stack[-1].append(t)
    return stack[0]
def q(s): return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
def dump(x, ind=0):
    if isinstance(x,list):
        if not x: return '()'
        head = dump(x[0])
        simple = all(not isinstance(e,list) for e in x)
        if simple and len(x)<12:
            return '('+' '.join(dump(e) for e in x)+')'
        parts=['('+head]
        for e in x[1:]:
            if isinstance(e,list): parts.append('\n'+'\t'*(ind+1)+dump(e,ind+1))
            else: parts.append(' '+dump(e))
        return ''.join(parts)+'\n'+'\t'*ind+')'
    if isinstance(x,Sym): return str(x)
    if isinstance(x,bool): return 'yes' if x else 'no'
    if isinstance(x,(int,)): return str(x)
    if isinstance(x,float):
        s=('%.4f'%x).rstrip('0').rstrip('.'); return s if s not in ('-0','') else '0'
    return q(x)
def find(node, key):
    return [e for e in node if isinstance(e,list) and e and e[0]==key]
def find1(node,key):
    r=find(node,key); return r[0] if r else None

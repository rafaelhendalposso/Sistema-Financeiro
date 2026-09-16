import csv
import datetime as dt
import json
import pathlib
import re
import uuid

ROOT = pathlib.Path('/private/tmp/notion-export/raw')
OUT = pathlib.Path('dist/notion-migration.json')


def uid():
    return str(uuid.uuid4())


def read(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def parse_amount(value):
    value = str(value or '').replace('\xa0', ' ').replace('R$', '').strip()
    if not value:
        return 0
    if ',' in value:
        value = value.replace('.', '').replace(',', '.')
    try:
        return round(float(value) * 100)
    except ValueError:
        return 0


MONTHS = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
    'outubro': 10, 'novembro': 11, 'dezembro': 12,
}


def month_from_relation(value):
    m = re.search(r'(\d{2})/(\d{4})', value or '')
    return f'{m.group(2)}-{m.group(1)}' if m else ''


def parse_date(value, month=''):
    raw = str(value or '').strip()
    if re.fullmatch(r'\d{8}', raw):
        try:
            return dt.datetime.strptime(raw, '%d%m%Y').date().isoformat()
        except ValueError:
            return ''
    if re.fullmatch(r'\d{1,2}', raw) and month:
        try:
            return dt.date(int(month[:4]), int(month[5:7]), int(raw)).isoformat()
        except ValueError:
            return ''
    m = re.search(r'(\d{1,2}) de ([^ ]+) de (\d{4})', raw.lower())
    if m:
        mon = MONTHS.get(m.group(2).replace('ã', 'a'))
        if mon:
            try:
                return dt.date(int(m.group(3)), mon, int(m.group(1))).isoformat()
            except ValueError:
                return ''
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
        return raw
    return ''


def impact(value):
    n = len(re.findall('⭐', value or ''))
    return n if 1 <= n <= 5 else 3


def rows_by_file():
    out = {}
    for p in sorted(ROOT.glob('*.csv')):
        with p.open(encoding='utf-8-sig', newline='') as f:
            out[p.name] = list(csv.DictReader(f))
    return out


files = rows_by_file()
expenses = files['0013_Despesas_107fd90e9c878344b60301f86c2ef70a_all.csv']
income = files['0012_Receitas_91bfd90e9c878200a07e017a48a09188_all.csv']
transfers = files['0016_Transfer_ncias_39ee1b0d07fb40d59e230f28b4e66d34_all.csv']
fixed = files['0010_Gastos_fixos_957db58034ef4010a535d77eda025233_all.csv']
goals = files['0011_Objetivos_d0fc969368a141618766ad4a97f1817a_all.csv']
summaries = files['0014_Resumo_85bfd90e9c8783189426814c92f9469e_all.csv']
salary_rows = files['0009_Divis_o_R_I_e_LS_397fd90e9c878081b307eb2421a78a55_all.csv']

accounts = [
    {'id': uid(), 'name': 'C6', 'kind': 'checking', 'opening': 0, 'openingDate': '2026-03-01', 'color': '#147d64'},
    {'id': uid(), 'name': 'Nubank', 'kind': 'checking', 'opening': 0, 'openingDate': '2026-03-01', 'color': '#7357b8'},
    {'id': uid(), 'name': 'Dinheiro vivo', 'kind': 'cash', 'opening': 0, 'openingDate': '2026-03-01', 'color': '#c15b45'},
    {'id': uid(), 'name': 'C6 — Guardado', 'kind': 'saving', 'opening': 0, 'openingDate': '2026-03-01', 'color': '#536477'},
    {'id': uid(), 'name': 'C6 - Crédito garantido', 'kind': 'guarantee', 'opening': 0, 'openingDate': '2026-03-01', 'color': '#8b6a42'},
]
account_id = {a['name']: a['id'] for a in accounts}

categories = []
cat_id = {}


def category(name, kind):
    name = (name or 'Outros').strip() or 'Outros'
    key = (name, kind)
    if key not in cat_id:
        c = {'id': uid(), 'name': name, 'type': kind}
        cat_id[key] = c['id']
        categories.append(c)
    return cat_id[key]


for name in ['Assinaturas', 'Alimentação', 'Kehl', 'Compras Online', 'Outros', 'Lazer', 'Jogo', 'Transporte', 'DAS', 'Compras pessoais', 'Guardar']:
    category(name, 'expense')
for name in ['Salário', 'Extra', 'Sobrou do mês passado']:
    category(name, 'income')

transactions = []
unmapped = []
expense_transaction_by_key = {}


def add_transaction(type_, description, amount, date, account, category_id='', notes='', **extra):
    if not amount or not date or account not in account_id:
        return None
    t = {
        'id': uid(), 'type': type_, 'description': description[:180], 'amount': amount,
        'date': date, 'accountId': account_id[account], 'toAccountId': '',
        'categoryId': category_id, 'paymentCardId': '', 'notes': notes[:2000], 'extra': extra,
    }
    transactions.append(t)
    return t


for row in expenses:
    amount = parse_amount(row.get('Valor'))
    if not amount:
        continue
    month = month_from_relation(row.get('Mês', ''))
    date = parse_date(row.get('Data de saída'), month)
    item = (row.get('Item') or '').strip()
    account = (row.get('Saiu de') or '').strip()
    tag = (row.get('Tag') or 'Outros').strip() or 'Outros'
    if not item or not date or account not in account_id:
        unmapped.append({'source': 'Despesas', 'row': row, 'reason': 'descrição, data ou conta ausente'})
        continue
    notes = (row.get('OBS') or '').strip()
    if tag == 'Guardar':
        t = {
            'id': uid(), 'type': 'transfer', 'description': f'Guardar · {item}', 'amount': amount,
            'date': date, 'accountId': account_id[account], 'toAccountId': account_id['C6 — Guardado'],
            'categoryId': '', 'paymentCardId': '', 'notes': notes[:2000],
            'extra': {'notionSource': 'Despesas', 'notionTag': tag, 'notionRaw': row},
        }
        transactions.append(t)
    else:
        t = add_transaction('expense', item, amount, date, account, category(tag, 'expense'), notes,
                            notionSource='Despesas', notionTag=tag, notionRaw=row)
        expense_transaction_by_key[(item.lower().strip(), date, amount)] = t


for row in income:
    amount = parse_amount(row.get('Valor'))
    if not amount:
        continue
    month = month_from_relation(row.get('Mês', ''))
    date = parse_date(row.get('Data de entrada'), month)
    source = (row.get('Fonte') or '').strip() or 'Sem fonte (Notion)'
    account = (row.get('Entrou em') or '').strip()
    tag = (row.get('Tag') or 'Extra').strip() or 'Extra'
    if not date or account not in account_id:
        unmapped.append({'source': 'Receitas', 'row': row, 'reason': 'data ou conta ausente'})
        continue
    add_transaction('income', source, amount, date, account, category(tag, 'income'), (row.get('OBS') or '').strip(),
                    notionSource='Receitas', notionTag=tag, notionRaw=row)


for row in transfers:
    amount = parse_amount(row.get('Valor'))
    date = parse_date(row.get('Data'), month_from_relation(row.get('Mês', '')))
    origin = (row.get('Origem') or '').strip()
    destination = (row.get('Destino') or '').strip()
    if not amount or not date or origin not in account_id or destination not in account_id:
        unmapped.append({'source': 'Transferências', 'row': row, 'reason': 'valor, data ou conta ausente'})
        continue
    transactions.append({'id': uid(), 'type': 'transfer', 'description': f'Transferência · {(row.get("Transferência") or "").strip()}',
                         'amount': amount, 'date': date, 'accountId': account_id[origin], 'toAccountId': account_id[destination],
                         'categoryId': '', 'paymentCardId': '', 'notes': '', 'extra': {'notionSource': 'Transferências', 'notionRaw': row}})


def target(name, fallback=0):
    row = next((r for r in summaries if (r.get('Nome') or '').startswith('09/2026')), {})
    raw = row.get(name) or ''
    value = parse_amount(raw)
    if not value:
        match = re.search(r'(?:R\$\s*)?([\d.]+(?:,\d+)?)\s*$', raw.replace('\xa0', ' '))
        if match:
            value = parse_amount(match.group(1))
    return value or fallback


projects = []
project_id = {}
for row in goals:
    name = (row.get('Projeto') or '').strip()
    if name and name not in project_id:
        project_id[name] = uid()
        projects.append({'id': project_id[name], 'name': name, 'archived': False})

goal_status = {'Não concluído': 'planned', 'A Entregar': 'bought', 'Concluído': 'delivered', 'Desistido': 'cancelled'}
goals_out = []
for row in goals:
    name = (row.get('Objetivo') or '').strip()
    if not name:
        unmapped.append({'source': 'Objetivos', 'row': row, 'reason': 'nome ausente'})
        continue
    status = goal_status.get((row.get('Status') or '').strip(), 'planned')
    paid_at = parse_date(row.get('Realizado')) or parse_date(row.get('Data entregue'))
    goal = {
        'id': uid(), 'name': name, 'target': parse_amount(row.get('Custo ~')),
        'saved': parse_amount(row.get('Custo ~')) if paid_at or status in ('delivered', 'bought') else 0,
        'projectId': project_id.get((row.get('Projeto') or '').strip(), ''),
        'priority': (row.get('Prioridade') or '').strip() or 'Ideia', 'impact': impact(row.get('Impacto')),
        'status': status, 'description': (row.get('Descrição') or '').strip(), 'url': (row.get('Link de compra') or '').strip(),
        'paidAt': paid_at, 'paidTransactionId': '',
        'extra': {'notionSource': 'Objetivos', 'notionRaw': row},
    }
    goals_out.append(goal)

recurring = []
for row in fixed:
    name = (row.get('Gasto') or '').strip()
    amount = parse_amount(row.get('Valor previsto'))
    paid_date = parse_date(row.get('Pago em'))
    if not name or not amount:
        unmapped.append({'source': 'Gastos fixos', 'row': row, 'reason': 'nome ou valor ausente'})
        continue
    day = int(row.get('Vence dia') or (paid_date or '2026-01-01')[8:10] or 1)
    rec_id = uid()
    rec = {'id': rec_id, 'name': name, 'amount': amount, 'day': max(1, min(31, day)), 'accountId': account_id['C6'],
           'categoryId': category('Assinaturas' if name == 'GPT' else 'Outros', 'expense'),
           'extra': {'notionSource': 'Gastos fixos', 'notionRaw': row, 'notionStatus': row.get('Status', '')}}
    recurring.append(rec)
    if paid_date:
        key = (name.lower().strip(), paid_date, amount)
        match = expense_transaction_by_key.get(key)
        if not match:
            match = next((t for t in transactions if t['type'] == 'expense' and t['date'] == paid_date and t['amount'] == amount and
                          (name.lower() in t['description'].lower() or t['description'].lower() in name.lower())), None)
        if match:
            match['recurringId'] = rec_id
            match['recurringMonth'] = paid_date[:7]
        else:
            paid = add_transaction('expense', name, amount, paid_date, 'C6', rec['categoryId'],
                                   'Importado de Gasto fixo pago; a conta não estava informada no Notion.',
                                   notionSource='Gastos fixos', notionRaw=row, recurringId=rec_id)
            if paid:
                paid['recurringId'] = rec_id
                paid['recurringMonth'] = paid_date[:7]

latest_targets = {
    'C6': target('C6 - Na conta'), 'Nubank': target('Nubank - Na conta'),
    'Dinheiro vivo': target('Dinheiro vivo (visual)'), 'C6 — Guardado': target('C6 - Guardado'),
    'C6 - Crédito garantido': target('Crédito garantido'),
}


def balance_delta(name):
    aid = account_id[name]
    total = 0
    for t in transactions:
        if t['accountId'] == aid:
            total += t['amount'] if t['type'] == 'income' else -t['amount']
        if t['type'] == 'transfer' and t['toAccountId'] == aid:
            total += t['amount']
    return total


for a in accounts:
    a['opening'] = latest_targets[a['name']] - balance_delta(a['name'])

salary = {'hours': 100, 'minutes': 47, 'rate': 1600, 'first': 'R.I', 'second': 'L.S', 'percent': 60, 'ownerOnly': True}
if salary_rows:
    row = salary_rows[0]
    try:
        salary['hours'] = int(float(row.get('Horas') or 100))
        salary['minutes'] = int(float(row.get('Minutos') or 47))
        salary['rate'] = parse_amount(row.get('R$/h')) or 1600
    except ValueError:
        pass

raw_files = {name: rows for name, rows in files.items()}
state = {
    'version': 2, 'accounts': accounts, 'categories': categories, 'transactions': transactions,
    'cards': [], 'purchases': [], 'payments': [], 'recurring': recurring, 'goals': goals_out,
    'projects': projects, 'investments': [], 'salary': salary,
    'settings': {
        'accent': '#147d64', 'palette': 'ocean', 'density': 'normal',
        'widgets': ['flow', 'accounts', 'recent', 'fixed'], 'fields': [],
        'overview': {'showInvestments': True, 'showAlerts': True, 'showGoals': True},
        'notionMigration': {
            'importedAt': dt.datetime.now().isoformat(timespec='seconds'),
            'sourcePages': [
                'https://app.notion.com/p/Gest-o-financeira-fcefd90e9c8782069af50155e9d995a1',
                'https://app.notion.com/p/Sistema-Financeiro-Pessoal-3dafd90e9c878166bab4f65e842f8560',
            ],
            'exportedAs': 'Notion Markdown e CSV', 'rawFiles': raw_files, 'unmappedRows': unmapped,
            'notes': [
                'As fórmulas e rollups do Notion foram preservadas nos CSVs brutos; os lançamentos usam os valores editáveis de origem.',
                'Itens com a tag Guardar viraram transferências para a conta C6 — Guardado, para não aparecerem como gasto.',
                'Não havia uma base específica de investimentos no export; por isso nenhum investimento foi inventado.',
            ],
        },
    },
}
OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'accounts': len(accounts), 'transactions': len(transactions), 'expenses': sum(t['type']=='expense' for t in transactions), 'income': sum(t['type']=='income' for t in transactions), 'transfers': sum(t['type']=='transfer' for t in transactions), 'goals': len(goals_out), 'recurring': len(recurring), 'projects': len(projects), 'unmapped': len(unmapped), 'latestTargets': latest_targets}, ensure_ascii=False))

from bottle import error, route, run, redirect, request, response, template
import psycopg2
import copy
from configparser import ConfigParser


def config(filename='connection.py', section='postgresql'):
	parser = ConfigParser() # create a parser
	parser.read(filename)
	db = {}
	if parser.has_section(section):
		params = parser.items(section)
		for param in params:
			db[param[0]] = param[1][1:-1]
	else:
		raise Exception('Section {0} not found in {1} '.format(section, filename))
	return db


def connect():
# connect to database
	global conn
	conn = psycopg2.connect(**db)
	conn.set_session(autocommit = True)
	cur = conn.cursor()
	return cur

def close(cur):
# close cursor and connection
	global conn
	try:
		cur.close();
	except:
		pass
	try:
		conn.close();
	except:
		pass

@route('/')
def hello():	
# main page, start search here
	return template('main')


@route('/', method='post')
def search():
# get user input from hello page
	mathematician = request.forms.get('Mathematician')
	theorem = request.forms.get('Theorem')
	year = request.forms.get('Year')

	if mathematician == "*" or theorem == "*" or year == "*": redirect('/invalid_char')
	if "_" in mathematician or "_" in theorem or "_" in year: redirect('/invalid_char')

	if len(mathematician) == 0: mathematician = "*"
	if len(theorem) == 0: theorem = "*"
	if len(year) == 0: year = "*"

	mathematician = mathematician.replace(" ", "_")
	theorem = theorem.replace(" ", "_")
	year = year.replace(" ", "_")

	redirect('/mathematician=%s/theorem=%s/year=%s' % (mathematician,theorem,year))


@route('/mathematician=<mathematician>/theorem=<theorem>/year=<year>')
def view_result(mathematician, theorem, year):
# redirected here after user hits search on the main page
	global cur
	if cur.closed: cur = connect()

	mathematician = mathematician.replace("_", " ")
	theorem = theorem.replace("_", " ")
	year = year.replace("_", " ")

	#q_mathmatician = "where attributedto ilike " + "'%" + "%s" % mathematician + "%'" if mathematician != "*" else ""
	#q_theorem = " name ilike " + "'%" + "%s" % theorem + "%'" if theorem != "*" else ""
	#q_year = " year = %s" % year if year != "*" else ""

	q_mathmatician = [" attributedto ilike " + "'%" + "%s" % mathematician + "%'"] if mathematician != "*" else []
	q_theorem = q_mathmatician + [" name ilike " + "'%" + "%s" % theorem + "%'"] if theorem != '*' else q_mathmatician
	q_year = q_theorem + [" year = " + year] if year != '*' else q_theorem
	if q_year != []: q = " where" + "and".join(q_year)
	else: q = ""

	query = "select * from theorem" + q + " order by year"
	#print(query)					
	cur.execute(query)
	res = template('result', cur = cur)
	close(cur)
	return res 


@route('/dependency/theorem=<theorem>')
def view_dep(theorem):
# linked from search result page - view dependency column
	global cur
	if cur.closed: cur = connect()
	theorem = theorem.replace("_", " ")
	cur.execute("select * from buildon where theorem1 ilike %s", [theorem,])
	res = template('dependency', cur = cur)
	close(cur)
	return res


@route('/del=<theorem>')
def del_record(theorem):
# delete theorem and direct to delete-success page	
	global cur
	if cur.closed: cur = connect()
	theorem = theorem.replace("_", " ")
	
	cur.execute("delete from theorem where name ilike %s", [theorem,])
	conn.commit()
	res = template('prompt', arg = ['Delete successful.', 'Successfully deleted theorem record'])
	close(cur)
	return res


@route('/invalid_del=<arg>')
def del_record():
# dead-end page for invalid delete
	return "<html><body>delete not supported for this table</body></html>"


@route('/view=<theorem>')
@route('/add_theorem')
def view_theorem(theorem='new'):
# linked from search result page - view/edit column
	global cur
	if cur.closed: 
		cur = connect()
		cur2 = connect()
	theorem = theorem.replace("_", " ")
	# get valid mathematician values to ensure FK constraint is enforced
	#print(theorem)
	cur2 = conn.cursor()
	cur2.execute("select knownas from mathematician")
	# case: adding theorem
	if theorem == 'new': return template('add_theorem', cur2 = cur2)
	# case: editing exsiting theorem
	cur.execute("select * from theorem where name ilike %s", [theorem,])
	cursors = {'cur':cur, 'cur2':cur2}
	res = template('edit_theorem', **cursors)
	close(cur)
	close(cur2)
	return res


@route('/view=<theorem>', method='post')
@route('/add_theorem', method='post')
def edit_theorem(theorem='new'):
# user clicks submit in the theorem view/edit page
	add = request.forms.get('add')
	if request.forms.get('theorem') != None: theorem = request.forms.get('theorem')
	aka = request.forms.get('aka')
	field = request.forms.get('field')
	year = request.forms.get('year')
	mathematician = request.forms.get('mathematician')

	#print(theorem, aka, field, year, mathematician)

	if theorem == "*" or aka == "*" or field == "*" or year == "*" or mathematician == "*": redirect('/invalid_char')
	if "_" in theorem or "_" in aka or "_" in field or "_" in year or "_" in mathematician: redirect('/invalid_char')
	if len(theorem) == 0: redirect('/edit_failure')
	if len(aka) == 0: aka = "*"
	if len(field) == 0: field = "*"
	if len(year) == 0: year = "*"
	if len(mathematician) == 0: mathematician = "*"

	theorem = theorem.replace(" ", "_")
	aka = aka.replace(" ", "_")
	field = field.replace(" ", "_")
	year = year.replace(" ", "_")
	mathematician= mathematician.replace(" ", "_")
	if add == 'true':
		redirect('add/theorem=%s/aka=%s/field=%s/year=%s/mathematician=%s' % (theorem,aka,field,year,mathematician))
	else:
		redirect('edit/theorem=%s/aka=%s/field=%s/year=%s/mathematician=%s' % (theorem,aka,field,year,mathematician))

@route('/edit_failure')
def error1_edit():
	arg = ['Failed to edit record', 'Primary key cannot be null.']
	return template('prompt', arg = arg)

@route('/invalid_char')
def error2_edit():
	arg = ['Invalid input', '"*" is invalid value, and "_" is not allowed.']
	return template('prompt', arg = arg)
	

@route('/<add>/theorem=<theorem>/aka=<aka>/field=<field>/year=<year>/mathematician=<mathematician>')
def success_add_edit_thm(add, theorem, aka, field, year, mathematician):
	global cur
	if cur.closed: cur = connect()

	theorem = theorem.replace("_", " ").replace("'", "''")
	aka = aka.replace("_", " ").replace("'", "''")
	field = field.replace("_", " ").replace("'", "''")
	mathematician = mathematician.replace("_", " ").replace("'", "''")

	#q_theorem = ['name']
	#q_aka = q_theorem+['othername'] if aka != '*' else q_theorem
	#q_field = q_aka+['field'] if field != '*' else q_aka
	#q_year = q_field+['year'] if year != '*' else q_field
	#q_mathematician = q_year+['attributedto'] if mathematician != '*' else q_year
	q = "(name, othername, field, year, attributedto)"
	
	v_theorem = [theorem]
	v_aka = v_theorem+[aka] if aka != '*' else v_theorem+['NULL']
	v_field = v_aka+[field] if field != '*' else v_aka+['NULL']
	v_year = v_field+[year] if year != '*' else v_field+['NULL']
	v_mathematician = v_year+[mathematician] if mathematician != '*' else v_year+['NULL']
	v = "('" + "','".join(v_mathematician) + "')"
	v = v.replace("'NULL'", "NULL")

	if add == 'add': query = "insert into theorem " + q + " values " + v
	else:  query = "update theorem set " + q + "= " + v + "where name = '" + theorem + "'"
	#print(query)
	try: cur.execute(query)
	except: return template('prompt', arg = ['Insert/Update Failed', \
		'Possible causes: 1) record or primary key already exists or 2) input value exceeded valid range or size'])
	conn.commit()
	close(cur)
	if add == 'add': return template('prompt', arg = ['Insert successful', 'Successfully inserted theorem record'])
	else: return template('prompt', arg = ['Edit successful', 'Successfully edited theorem record'])


@route('/dependency/add/theorem=<theorem>')
def edit_dependency(theorem):
# prepare to add dependency for a theorem
	global cur
	if cur.closed: cur = connect()
	cur.execute("select name from theorem")
	args = {'thm':theorem, 'cur':cur}
	res = template('add_dependency', **args)
	close(cur)
	return res


@route('/dependency/add/theorem=<theorem>', method='post')
def add_dependency(theorem):
# adding dependency for a theorem	
	global cur
	if cur.closed: cur = connect()
	cur.execute("select name from theorem")
	theorem2 = request.forms.get('theorem2')
	note1 = request.forms.get('Note1').replace(" ","_")
	note2 = request.forms.get('Note2').replace(" ","_")
	if len(note1) == 0: note1 = "*"
	if len(note2) == 0: note2 = "*"
	rng = [tup[0] for tup in cur]
	close(cur)
	if theorem2 in rng:
		theorem2 = theorem2.replace(" ", "_")
		redirect('/dependency/add/theorem1=%s/theorem2=%s/note1=%s/note2=%s' % (theorem, theorem2, note1, note2))
	else:
		return template('prompt', arg = ['Add dependency failed', 'Parent theorem needs to be in the theorem table']) 


@route('/dependency/add/theorem1=<theorem1>/theorem2=<theorem2>/note1=<note1>/note2=<note2>')
def success_add_dep(theorem1, theorem2, note1, note2):
	global cur
	if cur.closed: cur = connect()
	theorem1 = theorem1.replace("_", " ")
	theorem2 = theorem2.replace("_", " ")
	note1 = note1.replace("_", " ")
	note2 = note2.replace("_", " ")
	if note1 == "*": note1 = " " # because note1 and 2 are unimportant, we tolerate " " in place of null
	if note2 == "*": note2  = " "
	try: 
		cur.execute("insert into buildon values (%s, %s, %s, %s)", [theorem1,theorem2, note1, note2])
		close(cur)
	except: return template('prompt', arg = ['Insert/Update Failed', \
		'Possible causes: 1) record or primary key already exists or 2) input value exceeded valid range or size'])
	return template('prompt', arg = ['Add dependency successful', ''])


@route('/dep_del/theorem1=<theorem1>/theorem2=<theorem2>')
def del_dependency(theorem1, theorem2):
	global cur
	if cur.closed: cur = connect()
	theorem1 = theorem1.replace("_", " ")
	theorem2 = theorem2.replace("_", " ")
	cur.execute("delete from buildon where theorem1 = %s and theorem2 = %s", [theorem1,theorem2])
	close(cur)
	return template('prompt', arg = ['Delete dependency successful', ''])


@error(404)
def error404(error):
	return template('prompt', arg = ['404 Not Found', ''])

# create connection
db = config()
conn = psycopg2.connect(**db)
conn.set_session(autocommit = True)
cur = conn.cursor()

# start localhost
run(host="localhost", port=8080, debug=True)


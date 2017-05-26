#!/usr/bin/python

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import Gdk
import psycopg2 as pg
from types import MethodType

import datetime
import time

def deny_chars( ch ):
    def f( v ):
        for c in ch:
            if c in v:
                raise ValueError( 'value musn\'t contain any of %s' % ch )
    return f
db_chk_str = deny_chars( '\'"\\\b\t%\0' )

def allow_chars( ch ):
    def f( v ):
        for c in v:
            if c not in ch:
                raise ValueError( 'value must contain only characters %s' % ch )
    return f
tel_chk_str = allow_chars( '+0123456789' )
num_chk_str = allow_chars( '0123456789' )

def sel_chk( v ):
    if v is None:
        raise ValueError( 'choose something' )

def date_cvt( v ):
    # return datetime.strptime( v, '%Y-%m-%d' ).date() # FIXME: strange memory crash
    return datetime.date(*[ int(i) for i in v.split('-') ])

def len_checker( mn=0, mx=128 ):
    def f( v ):
        if mx < len(v): raise ValueError( 'value too long( max: %d )'  % mx )
        if mn > len(v): raise ValueError( 'value too short( min: %d )' % mn )
    return f

class in_str:
    def __init__( s, dv='' ):
        s.dv = dv
    def show( s, fd, v ):
        r = Gtk.Entry()
        r.set_width_chars( 24 )
        fd.rw( r )
        r.connect( 'changed', fd.entry_edited )
        r.connect( 'activate', fd.activated )
        #r.connect( 'key-press-event', lambda w,e: print(e.keyval,e.hardware_keycode,e.send_event) )
        r.set_text( v )
        r.set_max_length( 128 )

class in_txt:
    def __init__( s, dv='' ):
        s.dv = dv
    def show( s, fd, v ):
        r = Gtk.TextView()
        fd.rw( r )
        #r.set_policy( Gtk.Policy.NEVER, Gtk.Policy.ALWAYS )
        #r.set_wrap_mode( Gtk.Wrap.WORD )
        r.set_vexpand(True)
        r.set_hexpand(True)
        b = r.get_buffer()
        b.connect( 'changed', fd.buffer_edited )
        b.set_text( v )

class in_date:
    def __init__( s, dv=(1990,1,1) ):
        s.dv = dv
    def show( s, fd, v ):
        r = Gtk.Calendar()
        fd.rw( r )
        r.connect( 'day-selected', fd.calendar_edited )
        r.connect( 'month-changed', fd.calendar_edited )
        r.connect( 'day-selected-double-click', fd.activated )
        r.select_day( dv[2] )
        r.select_month( dv[1], dv[0] )

class col_descr:
    def __init__( s, n ):
        s.__dict__.update(locals())
        delattr(s,'s')
        #s.t = GdkPixbuf.Pixbuf
        s.t = str
    def col( s, it ):
        #class tst( Gtk.CellRendererPixbuf ):
        #    def activate( *args ):
        #        print(args)
        r = Gtk.CellRendererText() #Gtk.CellRendererPixbuf()
        #r.set_property( 'mode', Gtk.CellRendererMode.ACTIVATABLE )
        #r.set_property( 'sensitive', True )
        #r.set_property( 'editable', True)
        #r.activate = lambda *args: print(args)
        c = Gtk.TreeViewColumn( s.n, r, text=it ) #pixbuf=it )
        c.connect( 'clicked', lambda *args: print(args) )
        return c

# TODO: editable cells
class in_list:
    def __init__( s, cd, sf, dv=None, act=False ):
        s.__dict__.update(locals())
        delattr( s, 's' )
    def show( s, fd, v ):
        r = Gtk.ScrolledWindow()
        fd.rw( r )
        r.set_vexpand(True)
        r.set_hexpand(True)
        dl = s.sf()
        ls = Gtk.ListStore(*[ c.t for c in s.cd ])
        for l in dl:
            ls.append(l)
        tv = Gtk.TreeView.new_with_model( ls )
        sl = tv.get_selection()
        sl.set_mode( Gtk.SelectionMode.MULTIPLE )
        for i,c in enumerate( s.cd ):
            tv.append_column( c.col( i ) )
        r.add(tv)
        sl.connect( 'changed',
                fd.sel_edited_single if not s.act
                else lambda t: (fd.sel_edited_single(t),fd.activated())
        )
        tv.connect( 'row-activated', fd.activated )
        # TODO: set default on start

class act_btn:
    def __init__( s, a, bd=False, img=None, txt=None, hint=None ):
        s.__dict__.update(locals())
        delattr(s,'s')
    def show( s, o ):
        r = Gtk.Button()
        r.get_style_context().add_class( 'act' )
        if s.img:
            r.set_image( s.img )
            if s.txt:
                r.set_tooltip_text( s.txt )
        else:
            r.set_label( s.txt )
        if s.hint:
            r.set_tooltip_text( s.hint )
        if not s.bd:
            r.set_relief( Gtk.ReliefStyle.NONE )
        n = s.a
        r.connect( 'clicked', lambda bb: getattr( o, n )() )
        return r

class act_descr:
    def __init__( s, n, f ):
        s.__dict__.update(locals())
        delattr(s,'s')
    def setup_func( s, o ):
        f = s.f
        def af( s, *args ):
            try:
                s.print_err( 'processing...' )
                f( s.d, s )
                s.print_err('')
            except ValueError as e:
                s.print_err( 'value error: ' + str( e ) )
            return True
        setattr( o, s.n, MethodType( af, o ) )

class item_hider:
    class obj:
        def show( s, *args ): # TODO: loading spinner
            if hasattr( s, 'tt' ):
                GObject.source_remove( s.tt )
                delattr( s, 'tt' )
            s.clr()
            w = s.sf()
            w.show_all()
            s.h.add( w )
            s.h.set_reveal_child( True )
        def hide( s, *args ):
            s.h.set_reveal_child( False )
            s.tt = GObject.timeout_add( s.h.get_transition_duration(), s.clr )
        def vneg( s, *args ):
            if s.h.get_reveal_child():
                s.hide()
            else: s.show()
        def cont( s ):
            return s.h
        def clr( s ):
            c = s.h.get_children()
            for i in c:
                s.h.remove( i )
            if hasattr( s, 'tt' ): delattr( s, 'tt' )

    def __init__( s, tm=350 ):
        s.__dict__.update(locals())
        delattr(s,'s')
    def show( s, sf ):
        r = s.obj()
        r.h = Gtk.Revealer()
        r.h.set_transition_duration( s.tm )
        r.sf = sf
        r.clr()
        return r


class field:
    class obj:
        def __init__( s, od, fp ):
            s.__dict__.update(locals())
            delattr(s,'s')
        def entry_edited( s, e ):
            s.od.update( s, e.get_text() )
        def buffer_edited( s, e ):
            s.od.update( s, e.get_text(e.get_start_iter(),e.get_end_iter(),True) )
        def calendar_edited( s, c ):
            s.od.update( s, c.get_date() )
        def sel_edited_single( s, sel ):
            m,l = sel.get_selected_rows()
            if not l:
                s.od.update( s, None )
                return
            if len( l ) > 1:
                for i in l[1:]:
                    sel.unselect_path( i )
            it = m.get_iter( l[0] )
            v = m.get_value( it, 0 )
            s.od.update( s, v )
        def activated( s, *args ):
            s.fp.submit()
        def print_err( s, e ):
            if hasattr( s, 'el' ):
                s.el.set_text( e )
            if len(e): # set error style
                s.w.get_style_context().add_class( 'in_err' )
            else:
                s.w.get_style_context().remove_class( 'in_err' )
        def rw( s, w ):
            s.w = w
        def cont( s ):
            return s.w

    def __init__( s, d, vn, in_obj, chk_list, hint=None, exp=False, err=True ):
        s.__dict__.update(locals())
        delattr(s,'s')
    def show( s, fp ):
        o = s.obj( s, fp )
        if s.err:
            o.el = Gtk.Label()
            o.el.get_style_context().add_class( 'einfo' )
        dv = fp.get(s.vn,s.in_obj.dv)
        s.in_obj.show( o, dv )
        s.update( o, dv )
        if s.hint:
            o.w.set_tooltip_text( s.hint )
#            box.set_has_tooltip(True)
#            box.connect("query-tooltip", s.hint_func() )
        return o
    def update( s, o, v ):
        try:
            for f in s.chk_list:
                f( v )
            o.fp.mark_ok( s.vn )
            o.print_err( '' ) # TODO: error set function
            o.fp.set( s.vn, v )
        except ( ValueError, TypeError ) as e:
            o.print_err( str( e ) )
            o.fp.mark_err( s.vn )
            return
#    def hint_func( s ):
#        h = s.hint
#        def r( w, x, y, km, t ):
#            t.set_text( h )
#            return True
#        return r

class form:
    class obj:
        def __init__( s, d={}, l=set() ):
            s.__dict__.update(locals())
            delattr(s,'s')
            s.get = s.d.get
            #s.l.update(s.d.keys())
        def set( s, n, v ):
            s.d[n]=v
        def close( s ):
            s.w.destroy()
        def already_submitted( s, bb ):
            pass
        def mark_err( s, vn ):
            s.l.add( vn )
        def mark_ok( s, vn ):
            s.l.discard( vn )
        def add_action( s, a ):
            a.setup_func( s )
        def cancel( s, *args ):
            s.close()
        def print_err( s, e ):
            s.el.set_text( e )
        def reok( s ):
            delattr( s, 'submit' ) # FIXME: try ?
        def chk( s ):
            if s.l:
                raise ValueError( 'fill all fields correctly' )
        def cont( s ):
            return s.w

    def __init__( s, n, d, t, ab=[] ):
        s.__dict__.update(locals())
        del s.s
    def show( s, af, r=None ):
        if not r: r = s.obj();
        for f in af:
            r.add_action( f )
        #w = Gtk.Frame(orientation=)
        #w.set_title( s.n )
        pb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        #w.add( pb )
        pb.add( Gtk.Label( s.d ) )
        t = Gtk.Grid() # (2, len(s.t), False);
        pb.add( t )
        r.w = pb
        n_row = 0
        for i in s.t: # TODO: allow other object types
            fo = i.show( r )
            opt = {}
            if i.d:
                t.attach( Gtk.Label(i.d+': '), 0, n_row, 1, 1 )
                t.attach( fo.cont(), 1, n_row, 1, 1 )
            else:
                t.attach( fo.cont(), 0, n_row, 2, 1 )
            if hasattr( fo, 'el' ):
                t.attach( fo.el, 2, n_row, 1, 1 )
            n_row+=1
        box_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        r.el = Gtk.Label()
        pb.add( r.el )
        pb.add( box_btn )
        for i in s.ab:
            b = i.show( r )
            box_btn.pack_start( b, False, True, 20 )
        w.show_all()
        return r

class touch_kbd:
    class obj:
        def __init__( s, b, w ):
            s.__dict__.update(locals())
            del s.s
        def kp( s, bb, k, kc ):
            e = Gdk.Event()
            e.type = Gdk.EventType.KEY_PRESS
            e.keyval = k
            e.window = s.w.get_root_window()
            e.hardware_keycode = kc
            #print(e.keyval,e.hardware_keycode,e.send_event)
            s.w.emit( 'key-press-event', e )
        def cont( s ):
            return s.b
    def __init__( s ):
        pass
    def btn( s, t, o, k, cl ):
        r = Gtk.Button() #TODO: style class
        r.get_style_context().add_class( cl )
        w = Gtk.Grid()
        r.add(w)
        w.attach(Gtk.Label(t),0,0,1,1)
        im = Gtk.Image() # TODO: change image on mouse over leave-notify-event, enter-notify-event
        im.set_from_file( 'play.png' ) # TODO: cache image
        w.attach(im,0,0,1,1)
        r.set_can_focus( False )
        r.set_relief( Gtk.ReliefStyle.NONE )
        vv, keys = Gdk.Keymap.get_default().get_entries_for_keyval( k ) # TODO: global keymap variable
        if vv: # TODO: log error if False
            r.connect( 'clicked', o.kp, k, keys[0].keycode )
        return r
    def show( s, w ):
        b = Gtk.Grid()
        r = s.obj( b, w )
        for i in range( 9 ):
            b.attach( s.btn( str(i+1), r, ord(str(i+1)), 'num' ), i%3, i/3, 1, 1 )
        b.attach( s.btn( '0', r, ord('0'), 'num' ), 1, 3, 1, 1 )
        b.attach( s.btn( '←', r, Gdk.KEY_BackSpace, 'del' ), 2, 3, 1, 1 )
        b.attach( s.btn( '↓', r, Gdk.KEY_Tab, 'mv' ), 0, 3, 1, 1 )
        b.attach( s.btn( '«', r, Gdk.KEY_Left, 'arrow' ), 0, 4, 1, 1 )
        b.attach( s.btn( '»', r, Gdk.KEY_Right, 'arrow' ), 2, 4, 1, 1 )
        b.attach( s.btn( 'OK', r, Gdk.KEY_Return, 'enter' ), 1, 4, 1, 1 )
        return r

class dbconn:
    def connect( s, **params ):
        s.hh = pg.connect( **params )
        s.hh.autocommit = True # TODO: commit after whole transaction
        s.cc = s.hh.cursor(  )
        s.ff = None
    def insert( s, t, d, rid=False ):
        nn, vv = zip( * d.items() )
        nn = ','.join(nn)
        vv = ','.join(["'"+str(v)+"'" for v in vv])
        opt = ''
        if rid:
            opt += 'RETURNING id'
        q = ('INSERT INTO %s(%s) VALUES(%s) '+opt) % ( t, nn, vv )
        print( q )
        s.cc.execute( q )
        if rid:
            r = s.cc.fetchone()[0]
            print( 'id=', r )
            return r
    def update( s, t, d, cond ):
        if len(cond)<4: #raise ValueError( "condition '%s' too short" % ( cond ) )
            cond = 'id='+str(d.id)
        vv = ','.join([n+"='"+str(v)+"'," for n,v in d.keys()])
        s.cc.execute( 'UPDATE %s SET %s WHERE (%s)' % ( t, vv, cond ) )
    def first( s, t, cond, nt=['*'] ):
        s.cc.execute( 'SELECT %s FROM %s WHERE (%s)' % ( ','.join(nt), t, cond ) )
        row = s.cc.fetchall()
        return dict(zip(row[0],row[1]))
    def all( s, t, cond, nt=['*'] ): # TODO: limit
        s.cc.execute( 'SELECT %s FROM %s WHERE (%s)' % ( ','.join(nt), t, cond ) )
        row = s.cc.fetchall()
        return row[1:]

class frm( dict ):
    def extract( s, *l, **d ):
        r = {n:s[n] for n in l}
        r.update({ n:s[nr] for n,nr in d.items() })
        return r
    def insert( s, **d ):
        s.update( d )

#aa = win_form('a','aa',[
#    field_descr( 'oo', 'o', in_str(), [ deny_chars('1234&^&*'), len_checker( 1, 5 ) ] ),
#    field_descr( 'Nazwa', 'n', in_str(), [ len_checker( 3, 10 ) ] ),
#    ], lambda v: print(v))


style = open( 'style.css', 'rb' ).read()
style_provider = Gtk.CssProvider()
style_provider.load_from_data(style)

Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(),
    style_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)

w = Gtk.Window( title='Dodaj pacjenta' )
pb = Gtk.Box( orientation=Gtk.Orientation.VERTICAL )
w.add( pb )

def pdata_submit( db, d ):
    d = frm(d)
    udata = d.extract( name='n', sname='ln', bdate='bd' )
    udata.update(dict( sex='?', password='', pid='', id_pid_type=1, idcard_type='', height=0, insurance_by_self=True, made_insurance_payments=True, insurer='', insurance_last_ver_date='2018-03-17', idcard_number='', contraindications='Brak', user_group='-' ))
    uid = db.insert( 'users.user', udata, rid=True )
    cid = db.insert( 'contact', d.extract(value='tel'), rid=True )
    db.insert( 'users.user_cont', dict( id_contact=cid, added_date=str(datetime.datetime.now()), id_user=uid ) )
    adata = d.extract( 'city', 'street', 'province', 'postal_code', 'country', 'street_number', 'building', 'unit' )
    adata.update( dict( hash='' ) )
    aid = db.insert( 'public.address', adata, rid=True )
    db.insert( 'users.user_adr', dict( id_address=aid, id_user=uid, added_date=str(datetime.datetime.now()) ) )

#"""
im = Gtk.Image()
im.set_from_file( 'play.png' )
aaa = form.obj()#d={'ln': 'Rosołek', 'postal_code': '00-770', 'street': 'Piwarskiego', 'building': '', 'tel': '601887554', 'street_number': '1', 'bd': '1987-08-06', 'country': 'PL', 'unit': '58', 'n': 'Rafał', 'province': 'Mazowieckie', 'city': 'Warszawa'})
aa = form('aa','Dodaj pacjenta',(
    field( 'Imię', 'n', in_str(), [ db_chk_str, len_checker( 3, 24 ) ], hint='Imię pacjenta' ),
    field( 'Nazwisko', 'ln', in_str(), [ db_chk_str, len_checker( 3, 24 ) ], hint='Nazwisko pacjenta' ),
    field( 'Data urodzenia', 'bd', in_str(), [ date_cvt ], hint='Data urodzenia pacjenta\nFormat: yyyy-mm-dd' ),
    field( 'Telefon', 'tel', in_str(), [ tel_chk_str, len_checker( 9, 12 ), db_chk_str ], hint='Numer telefonu pacjenta' ),
    field( 'Miasto', 'city', in_str(), [ db_chk_str, len_checker( 2, 24 ) ] ),
    field( 'Ulica', 'street', in_str(), [ db_chk_str, len_checker( 2, 24 ) ] ),
    field( 'Województwo', 'province', in_str(dv='Mazowieckie'), [ db_chk_str, len_checker( 3, 24 ) ] ),
    field( 'Kod pocztowy', 'postal_code', in_str(), [ db_chk_str, len_checker( 6, 6 ) ] ),
    field( 'Kraj', 'country', in_str(dv='PL'), [ db_chk_str, len_checker( 1, 2 ) ] ),
    field( 'Numer domu', 'street_number', in_str(), [ num_chk_str, len_checker( 1, 5 ) ] ),
    field( 'Budynek', 'building', in_str(), [ db_chk_str, len_checker( 0, 24 ) ] ),
    field( 'Numer mieszkania', 'unit', in_str(), [ num_chk_str, len_checker( 0, 4 ) ] ),
), ab=(
    act_btn( 'cancel', txt='Cancel' ),
    act_btn( 'submit', img=im, txt='Ok' ),
))#lambda v: print(v))
db = dbconn()
db.connect( dbname='forrest', user='iwasz' )
oo = aa.show((
#    act_descr('submit', lambda d, o: (o.chk(),print( d, o ),o.close())),
    act_descr('submit', lambda d, o: (o.chk(),print( str(d).encode(), o ),pdata_submit(db,d),w.destroy())), # o.chk()
    act_descr('cancel', lambda d, o: (print( d, o ),w.destroy())),
),aaa)
pb.add( oo.cont() )

#pb.add( touch_kbd().show(w).cont() )
 #"""

#im = GdkPixbuf.Pixbuf.new_from_file( 'play.png' )
#l = in_list( ( col_descr('a'), col_descr('b') ), lambda: [['1', '2'], ['3', '4']] )
#lambda: [[im, im], [im, im]] )
#w.add(l.show( None ))

"""
w = Gtk.Window( title='aaa' )
bb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
w.add(bb)
b = Gtk.Button( label='aaaaaa' )
bb.add(b)
h = item_hider()
hh = h.show( lambda: Gtk.Label('aaaaaaaaa\naaaaaaaaaaaa\naaaaaaaaaaa\naaaaaaaaaa\n\n\n\naaaaaa') )
b.connect( 'clicked', hh.vneg )
bb.add( hh.cont() )
w.connect( 'destroy', Gtk.main_quit )
w.show_all() #"""


w.connect( 'destroy', Gtk.main_quit )
w.show_all()

Gtk.main()



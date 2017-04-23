#!/usr/bin/python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import cairo
import psycopg2 as pg

class deny_chars:
    def __init__( s, ch ):
        s.ch = ch
    def chk( s, v ):
        for c in s.ch:
            if c in v:
                raise ValueError( 'value musn\'t contain any of %s' % s.ch )

class len_checker:
    def __init__( s, mn=0, mx=128 ):
        s.mx = mx
        s.mn = mn
    def chk( s, v ):
        if s.mx < len(v): raise ValueError( 'value too long( max: %d )'  % s.mx )
        if s.mn > len(v): raise ValueError( 'value too short( mix: %d )' % s.mn )

def input_str_edited( e, o ):
    o.od.update( o, e.get_text() )
class input_str:
    def __init__( s, dv='' ):
        s.dv = dv
    def show( s, o ):
        r = Gtk.Entry()
        r.set_max_length( 128 )
        r.connect( 'changed', input_str_edited, o )
        return r

class field_data:
    pass

class field_descr:
    def __init__( s, n, vn, in_obj, chk_list, descr=None ):
        s.n = n
        s.vn = vn
        s.in_obj = in_obj
        s.chk_list = chk_list
    def show( s, outd, lset ):
        o = field_data()
        o.od = s
        o.lset = lset
        o.outd = outd
        if s.n not in o.lset: o.lset.add( s.vn )
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add( s.in_obj.show( o ) )
        o.err_info = Gtk.Label( '' )
        box.add( o.err_info )
        if hasattr( o.outd, s.vn ): s.update( o, o.outd[s.vn] )
        else: s.update( o, s.in_obj.dv )
        return box
    def update( s, o, v ):
        for f in s.chk_list:
            try:
                f.chk( v )
            except ValueError as e:
                o.err_info.set_text( str( e ) )
                if s.vn not in o.lset: o.lset.add( s.vn )
                return
        if s.vn in o.lset: o.lset.remove( s.vn )
        o.err_info.set_text( '' )
        o.outd[ s.vn ] = v

class form_descr:
    def close( s ):
        s.w.destroy()

def win_form_already_clicked( o ):
    raise ValueError( 'button already clicked' )
def win_form_cancel( bb, f ):
    f.close()
def win_form_ok( bb, f, o ):
    try:
        if len(f.l)>0: raise ValueError( 'fill all fields correctly' )
        f.err_info.set_text( 'processing...' )
        o.func_next( f.d )
        f.close()
    except ValueError as e:
        f.err_info.set_text( 'value error: ' + str( e ) )
#    except Exception as e:
#        f.err_info.set_text( str( e ) )
class win_form:
    def __init__( s, n, d, t, func_next ):
        s.n = n
        s.d = d
        s.t = t
        s.func_next = func_next
    def show( s ):
        r = form_descr();
        w = Gtk.Window()
        w.set_title( s.n )
        pb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        w.add( pb )
        pb.add( Gtk.Label( s.d ) )
        t = Gtk.Table (2, len(s.t), False);
        pb.add( t )
        r.w = w
        r.d = {}
        r.l = set()
        n_row = 0
        for i in s.t:
            l = Gtk.Label(i.n+': ')
            #l.set_alignment(0, 0)
            t.attach( l, 0, 1, n_row, n_row+1 )
            t.attach( i.show( r.d, r.l ), 1, 2, n_row, n_row+1 )
            n_row+=1
        box_cnf = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        r.err_info = Gtk.Label()
        pb.add( r.err_info )
        pb.add( box_cnf )
        bcan = Gtk.Button( 'CANCEL' )
        bcan.connect('clicked', win_form_cancel, r)
        box_cnf.pack_start( bcan, False, True, 20 )
        bok = Gtk.Button( 'OK', s.func_next, r.d )
        box_cnf.pack_end( bok, False, True, 20  )
        bok.connect('clicked', win_form_ok, r, s)
        w.show_all()
        return r

class dbconn:
    def connect( s ):
        s.hh = pg.connect( "dbname='template1' user='dbuser' host='localhost' password='dbpass'" )
        s.cc = s.hh.cursor()
        s.ff = None
    def insert( s, t, d ):
        nn = ''
        vv = ''
        for n,i in d:
            nn += n+','
            vv += '\''+i+'\','
        s.cc.execute( 'INSERT INTO %s( %s ) VALUES( %s )' % ( t, nn, vv ) )
    def update( s, t, d, cond ):
        if len(cond)<10: raise ValueError( 'condition %s too short' % ( cond ) )
        vv = ''
        for n,i in d:
            vv += n+'=\''+i+'\','
        s.cc.execute( 'UPDATE %s SET %s WHERE ( %s )' % ( t, vv, cond ) )
    def select_one( s, t, cond, nt ):
        s.ff.execute( 'SELCT %s FROM %s WHERE ( %s )' % ( ','.join(nt), t, cond ) )
        row = s.ff.fetchall()
        r = {}
        for i in range( len( row[0] ) ):
            r[row[0][i]] = row[1][i]
        return r

#aa = win_form('a','aa',[
#    field_descr( 'oo', 'o', input_str(), [ deny_chars('1234&^&*'), len_checker( 1, 5 ) ] ),
#    field_descr( 'Nazwa', 'n', input_str(), [ len_checker( 3, 10 ) ] ),
#    ], lambda v: print(v))
#oo = aa.show()
#oo.w.connect( 'destroy', Gtk.main_quit )

def draw_page(operation=None, context=None, page_nr=None):
    ctx = context.get_cairo_context()
    w = context.get_width()
    h = context.get_height()
    ctx.set_source_rgb(0.5, 0.5, 1)
    ctx.rectangle(w*0.1, h*0.1, w*0.8, h*0.8)

    ctx.select_font_face( 'Purisa', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL )
    ctx.set_font_size( 13 )
    ctx.move_to( w*0.5, h*0.5 )
    ctx.show_text( '¤¤¤aaaaataaaaa¤¤¤' )
    ctx.stroke()

pd = Gtk.PrintOperation()
pd.set_n_pages(2)
pd.connect("draw_page", draw_page)
result = pd.run( Gtk.PrintOperationAction.PRINT_DIALOG, None )
print( result ) # handle errors etc.

#Gtk.main()



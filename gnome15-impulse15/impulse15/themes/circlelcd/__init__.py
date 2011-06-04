import math

fft = True

def load_theme( screenlet ):
	
	'''
	screenlet.resize( 300, 300 )

	screenlet.add_option( ColorOption(
		'Impulse', 'cc',
		cc, 'Color',
		'Example options group using color'
	) )
	'''


def on_after_set_attribute ( self, name, value, screenlet ):
	setattr( self, name, value )

def on_draw( audio_sample_array, cr, screenlet ):

	l = len( audio_sample_array )

	width, height = ( screenlet.width, screenlet.height )


	n_bars = screenlet.bars

	cr.set_line_width( screenlet.bar_width )

	for i in range( 0, l, l / n_bars ):
		bar_amp_norm = audio_sample_array[ i ]


		bar_height = ( bar_amp_norm * ( screenlet.width / 2 ) + screenlet.bar_width ) * ( screenlet.bar_height / 10.0 )

		cc = screenlet.col2
		cr.set_source_rgba( cc[ 0 ],  cc[ 1 ],  cc[ 2 ],  cc[ 3 ] )
		for j in range( 0, int( bar_height / 5 ), max(max(1, screenlet.spacing) / 5, 1) ):
			cr.arc(
				width / 2,
				height / 2,
				20 + j * screenlet.bar_width,
				( math.pi*2 / n_bars ) * ( i / ( l / n_bars ) ),
				( math.pi*2 / n_bars ) * ( i / ( l / n_bars ) + 1 ) - .05
			)

			cr.stroke( )
			
			if j == 0:		
				cc = screenlet.col1	
				cr.set_source_rgba( cc[ 0 ],  cc[ 1 ],  cc[ 2 ],  cc[ 3 ] )

peak_heights = [ 0 for i in range( 256 ) ]
peak_acceleration = [ 0.0 for i in range( 256 ) ]

def load_theme ( screenlet):
	pass

def on_draw ( audio_sample_array, cr, screenlet ):
	n_cols = screenlet.bars
	col_width = screenlet.bar_width
	col_spacing = screenlet.spacing
	bar_color = screenlet.col1
	row_height = screenlet.bar_height
	n_rows = screenlet.rows
	row_spacing = screenlet.spacing
	peak_color = screenlet.col2
	freq = len( audio_sample_array ) / n_cols
	actual_cols = ( len( audio_sample_array ) / freq ) + 1 
	
	total_width = ( actual_cols * ( col_width + col_spacing ) ) - col_spacing
	
#	print "Total width = %d, Cols = %d, width = %d, spacing = %d, freq = %f, len = %d, actual_cols = %d" % ( total_width, n_cols, col_width, col_spacing, freq, len(audio_sample_array), actual_cols  )
	
	cr.save()
	cr.translate( ( screenlet.width - total_width ) / 2, 0)

	for i in range( 0, len( audio_sample_array ), freq ):

		col = i / freq
		rows = int( audio_sample_array[ i ] * ( n_rows - 2 ) )

		cr.set_source_rgba( bar_color[ 0 ], bar_color[ 1 ], bar_color[ 2 ], bar_color[ 3 ] )

		if rows > peak_heights[ i ]:
			peak_heights[ i ] = rows
			peak_acceleration[ i ] = 0.0
		else:
			peak_acceleration[ i ] += .1
			peak_heights[ i ] -= peak_acceleration[ i ]

		if peak_heights[ i ] < 0:
			peak_heights[ i ] = 0

		for row in range( 0, rows ):

			cr.rectangle(
				col * ( col_width + col_spacing ),
				screenlet.height - row * ( row_height + row_spacing ),
				col_width, -row_height
			)

		cr.fill( )

		cr.set_source_rgba( peak_color[ 0 ], peak_color[ 1 ], peak_color[ 2 ], peak_color[ 3 ] )

		cr.rectangle(
			col * ( col_width + col_spacing ),
			screenlet.height - peak_heights[ i ] * ( row_height + row_spacing ),
			col_width, -row_height
		)

		cr.fill( )

	cr.fill( )
	cr.stroke( )
	cr.restore()


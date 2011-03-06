def load_theme( screenlet ):
	pass

def on_draw( audio_sample_array, cr, screenlet ):

	l = len( audio_sample_array )

	width, height = ( screenlet.width, screenlet.height )

	# start drawing spectrum


	n_bars = screenlet.bars
	bar_width = screenlet.bar_width
	bar_spacing = screenlet.spacing
	
	
	freq = len( audio_sample_array ) / n_bars
	actual_cols = ( len( audio_sample_array ) / freq ) + 1
	total_width = ( actual_cols * ( bar_width + bar_spacing ) ) - bar_spacing
	cr.translate( ( screenlet.width - total_width ) / 2, 0)

	for i in range( 0, l, l / n_bars ):

		bar_amp_norm = audio_sample_array[ i ]

		bar_height = bar_amp_norm * height + 2

		cr.rectangle(
			( bar_width + bar_spacing ) * ( i / ( l / n_bars ) ),
			height / 2 - bar_height / 2,
			bar_width,
			bar_height
		)
		
		co = screenlet.col1
		cr.set_source_rgba( co[ 0 ], co[ 1 ], co[ 2 ], co[ 3 ] )
		cr.fill_preserve()
		co = screenlet.col2
		cr.set_source_rgba( co[ 0 ], co[ 1 ], co[ 2 ], co[ 3 ] )
		cr.stroke()


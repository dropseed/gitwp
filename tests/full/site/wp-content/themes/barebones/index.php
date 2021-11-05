<?php get_header(); ?>
	<?php
	if ( have_posts() ) :

		while ( have_posts() ) :

			the_post();
			the_title();
			the_content();

		endwhile;

		the_posts_navigation();

	else :
	?>

		<p>Nothing to display</p>

	<?php
	endif;
	?>

<?php
get_sidebar();
get_footer();

<?php get_header(); ?>

	<?php
	while ( have_posts() ) :

		the_post();
		the_title();
		the_content();

		the_post_navigation();

		if ( comments_open() || get_comments_number() ) :
			comments_template();
		endif;

	endwhile;
	?>

<?php
get_sidebar();
get_footer();

<?php get_header(); ?>

	<?php if ( have_posts() ) : ?>

		<header>
			<h1>
				Search results for: <?php echo get_search_query(); ?>
			</h1>
		</header>

		<?php
		while ( have_posts() ) :

			the_post();
			the_title();
			the_excerpt();

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

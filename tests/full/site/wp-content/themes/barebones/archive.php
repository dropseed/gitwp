<?php get_header(); ?>

	<?php if ( have_posts() ) : ?>

		<header>
			<?php
			the_archive_title( '<h1>', '</h1>' );
			the_archive_description( '<div>', '</div>' );
			?>
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

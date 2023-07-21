<?php
/*
Plugin Name: GitWP Migrations
Description: Data migrations.
Version: 0.1.0
Author: Dave Gaeddert
*/

class GitWPMigrations {
    private $migrationsPath;
    private $ignorePatterns = array(
        // Ignore all SELECT and SHOW queries
        '/^\s*(SELECT|SHOW)/i',
        // Users
        '/wp_users/i',
        '/wp_usermeta/i',
        // Admin
        '/_edit_lock/i',
        // WooCommerce
        '/wp_wc_admin_note/i',
        '/wp_woocommerce_sessions/i',
        // Plugins
        '/WHERE `option_name` = \'recently_activated\'/i',
        // Other
        '/_transient_/i',
        '/wp_actionscheduler_/i',
        '/action_scheduler_/i',
        '/post_type = \'scheduled-action\'/i',
        '/jetpack_sync/i',
        '/jetpack_safe_mode_confirmed/i',
    );

    private $queryLog = array();

    // Add a static member to hold the instance
    public static $instance;

    public function __construct() {
        self::$instance = $this;

        $this->migrationsPath = dirname(ABSPATH) . '/migrations';
        $this->currentMigration = $this->findLockedMigration();
        if ($this->currentMigration) {
            define('SAVEQUERIES', true);
            add_filter('log_query_custom_data', array($this, 'storeQuery'), 99, 5);
            add_filter('shutdown', array($this, 'updateMigration'));
        }
    }

    public function storeQuery($query_data, $query, $query_time, $query_callstack, $query_start) {
        // Check if the query matches any of the ignore patterns
        foreach ($this->ignorePatterns as $pattern) {
            if (preg_match($pattern, $query)) {
                return $query;
            }
        }

        global $wpdb;

        // This is not running late enough to use this...
        // If it was an insert, get the id as result
        // if (preg_match('/^\s*INSERT/i', $query)) {
        //     $result = $wpdb->insert_id;
        // } else if (preg_match('/^\s*UPDATE/i', $query)) {
        //     $result = $wpdb->rows_affected;
        // } else if (preg_match('/^\s*DELETE/i', $query)) {
        //     $result = $wpdb->rows_affected;
        // } else {
        //     $result = $wpdb->result;
        // }
        if ( preg_match( '/^\s*(insert|replace)\s/i', $query ) ) {
            if ( $wpdb->use_mysqli ) {
                $result = mysqli_insert_id( $wpdb->dbh );
            } else {
                $result = mysql_insert_id( $wpdb->dbh );
            }
        } else {
            $result = null;  // null for now...
        }

        // Store the query in the query log
        $this->queryLog[] = array(
            'query' => $query,
            'result' => $result,
        );

        return $query;
    }

    public function getNextMigrationPath() {
        $migrations_dir = $this->migrationsPath;
        if (!file_exists($migrations_dir)) {
            mkdir($migrations_dir);
        }
        // The migration files will be named 0001_migration.json, 0002_migration.json, etc.
        $migration_files = glob($migrations_dir . '/*.json');
        sort($migration_files);
        // Parse the migration number from the last migration file
        $last_migration_file = end($migration_files);
        $last_migration_number = intval(basename($last_migration_file, '.json'));
        $next_migration_number = $last_migration_number + 1;
        $migration_file = $migrations_dir . '/' . str_pad($next_migration_number, 4, '0', STR_PAD_LEFT) . '_migration.json';
        return $migration_file;
    }

    public function findLockedMigration() {
        $migrations_dir = $this->migrationsPath;
        if (!file_exists($migrations_dir)) {
            return null;
        }
        // The migration files will be named 0001_migration.json, 0002_migration.json, etc.
        $migration_files = glob($migrations_dir . '/*.json.lock');
        sort($migration_files);
        // Parse the migration number from the last migration file
        $last_migration_file = end($migration_files);
        return $last_migration_file;
    }

    public function startMigration() {
        $path = $this->getNextMigrationPath();

        // Create a lockfile that tells WP that a migration is currently being created
        $lock_path = $path . '.lock';

        $migration = array(
            'queries' => $this->queryLog,
        );

        file_put_contents($lock_path, json_encode($migration, JSON_PRETTY_PRINT));

        return basename($path);
    }

    public function updateMigration() {
        // Load the migration file
        $migration = json_decode(file_get_contents($this->currentMigration), true);

        // Append the queries to the migration
        $migration['queries'] = array_merge($migration['queries'], $this->queryLog);

        // Save the migration file
        file_put_contents($this->currentMigration, json_encode($migration, JSON_PRETTY_PRINT));
    }

    public function finishMigration($path) {
        // load it, and if migrations are empty then delete it
        $migration = json_decode(file_get_contents($path), true);
        if (empty($migration['queries'])) {
            unlink($path);
            return 0;
        }

        // Rename the lock file to the final file
        $lock_path = $path . '.lock';
        rename($lock_path, $path);

        return count($migration['queries']);
    }
}

new GitWPMigrations();

class GitWP_CLI_Commands {
    /**
    * Starts a data migration.
    *
    * ## EXAMPLES
    *
    *     wp migrations start
    *
    * @when after_wp_load
    */
    function start( $args, $assoc_args ) {
        // Access the instance and start the migration
        $path = GitWPMigrations::$instance->startMigration();
        $name = basename($path);
        echo "Starting migration: $name\n";
        echo "Run `wp migrations finish` when done\n";
    }

    function finish ( $args, $assoc_args ) {
        $path = GitWPMigrations::$instance->findLockedMigration();
        if (!$path) {
            WP_CLI::error('No migration in progress');
        }

        $num_queries = GitWPMigrations::$instance->finishMigration($path);
        echo "Finished migration: $path ($num_queries queries)\n";
    }
}

if ( defined( 'WP_CLI' ) && WP_CLI ) {
    WP_CLI::add_command( 'migrations', 'GitWP_CLI_Commands' );
}

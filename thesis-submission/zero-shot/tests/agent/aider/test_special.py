import shutil
import tempfile
from pathlib import Path
import pytest

from masterthesis.agent.aider.AdvancedDiffAgent import (
    UnifiedDiffCoder,
    hunk_to_before_after,
)


@pytest.fixture
def setup_repo():
    repo_dir = tempfile.mkdtemp()
    Path(repo_dir).mkdir(exist_ok=True)
    test_file_path = Path(repo_dir) / "test_file.java"
    test_content = """
public class NisAppConfig {
	@Bean
	public DataSource dataSource() throws IOException {
		final NisConfiguration configuration = this.nisConfiguration();
		final String nemFolder = configuration.getNemFolder();
		final Properties prop = new Properties();
		prop.load(NisAppConfig.class.getClassLoader().getResourceAsStream("db.properties"));

		// replace url parameters with values from configuration
		final String jdbcUrl = prop.getProperty("jdbc.url").replace("${nem.folder}", nemFolder).replace("${nem.network}",
				configuration.getNetworkName());

		final DriverManagerDataSource dataSource = new DriverManagerDataSource();
		dataSource.setDriverClassName(prop.getProperty("jdbc.driverClassName"));
		dataSource.setUrl(jdbcUrl);
		dataSource.setUsername(prop.getProperty("jdbc.username"));
		dataSource.setPassword(prop.getProperty("jdbc.password"));
		return dataSource;
	}

	@Bean(initMethod = "migrate")
	public Flyway flyway() throws IOException {
		final Properties prop = new Properties();
		prop.load(NisAppConfig.class.getClassLoader().getResourceAsStream("db.properties"));

		final org.flywaydb.core.Flyway flyway = new Flyway();
		flyway.setDataSource(this.dataSource());
		flyway.setClassLoader(NisAppConfig.class.getClassLoader());
		flyway.setLocations(prop.getProperty("flyway.locations"));
		flyway.setValidateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")));
		return flyway;
	}

	@Bean
	@DependsOn("flyway")
	public SessionFactory sessionFactory() throws IOException {
		return SessionFactoryLoader.load(this.dataSource());
	}
}
"""

    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    diff_content = """\
```diff
diff --git a/test_file.java b/test_file.java
@@ - final org.flywaydb.core.Flyway flyway = new Flyway();
- flyway.setDataSource(this.dataSource());
- flyway.setClassLoader(NisAppConfig.class.getClassLoader());
- flyway.setLocations(prop.getProperty("flyway.locations"));
- flyway.setValidateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")));
+ final org.flywaydb.core.Flyway flyway = Flyway.configure()
+ .dataSource(this.dataSource())
+ .classLoader(NisAppConfig.class.getClassLoader())
+ .locations(prop.getProperty("flyway.locations"))
+ .validateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")))
+ .load();
```"""



    coder = UnifiedDiffCoder(repo_dir)

    yield coder, diff_content, test_file_path

    shutil.rmtree(repo_dir)


def test_apply_edits(setup_repo, snapshot):
    coder, diff_content, test_file_path = setup_repo
    success, result = coder.apply_edits(diff_content)
    assert success

    expected_result = """\

"""
    assert result == snapshot
    # assert result.strip() == expected_result.strip()


# def test_apply_hunk(setup_repo):
#     coder, _, test_file_path = setup_repo
#     with open(test_file_path, "r", encoding="utf-8") as f:
#         content = f.read()

#     hunk = [
#         "- final org.flywaydb.core.Flyway flyway = new Flyway();",
#         "- flyway.setDataSource(this.dataSource());",
#         "- flyway.setClassLoader(NisAppConfig.class.getClassLoader());",
#         "- flyway.setLocations(prop.getProperty("flyway.locations"));",
#         "- flyway.setValidateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")));",
#         "+ final org.flywaydb.core.Flyway flyway = Flyway.configure()",
#         "+ .dataSource(this.dataSource())",
#         "+ .classLoader(NisAppConfig.class.getClassLoader())",
#         "+ .locations(prop.getProperty("flyway.locations"))",
#         "+ .validateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")))",
#         "+ .load();"
#     ]

#     result = coder.apply_hunk(content, hunk)
#     expected_result = """\
# @Bean(initMethod = "migrate")
# public Flyway flyway() throws IOException {
#     final Properties prop = new Properties();
#     prop.load(NisAppConfig.class.getClassLoader().getResourceAsStream("db.properties"));

#     final org.flywaydb.core.Flyway flyway = Flyway.configure()
#     .dataSource(this.dataSource())
#     .classLoader(NisAppConfig.class.getClassLoader())
#     .locations(prop.getProperty("flyway.locations"))
#     .validateOnMigrate(Boolean.valueOf(prop.getProperty("flyway.validate")))
#     .load();
#     return flyway;
# }"""
#     assert result.strip() == expected_result.strip()

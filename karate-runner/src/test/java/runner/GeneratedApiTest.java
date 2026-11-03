package runner;
import com.intuit.karate.junit5.Karate;
class GeneratedApiTest {
    @Karate.Test
    Karate runGeneratedApiTests() {
        return Karate.run("classpath:features/generated.feature");
    }
}

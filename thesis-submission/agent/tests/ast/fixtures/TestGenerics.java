import java.util.ArrayList;
import test.de.SuperString;
public class TestGenerics {
    public void testMethod() {
        ArrayList<String> list = new ArrayList<>();
        list.add("Test");

        ArrayList<SuperString> list2 = new ArrayList<>();
        list2.add(new SuperString("Test"));
    }
}

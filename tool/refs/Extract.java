import java.awt.Shape;
import java.awt.geom.*;
import java.lang.reflect.*;
import java.util.Locale;

public class Extract {
  static String pathToSVG(Shape s) {
    PathIterator pi = s.getPathIterator(null);
    double[] c = new double[6];
    StringBuilder d = new StringBuilder();
    while (!pi.isDone()) {
      int t = pi.currentSegment(c);
      switch (t) {
        case PathIterator.SEG_MOVETO:  d.append(String.format(Locale.US,"M%.2f %.2f ", c[0], c[1])); break;
        case PathIterator.SEG_LINETO:  d.append(String.format(Locale.US,"L%.2f %.2f ", c[0], c[1])); break;
        case PathIterator.SEG_QUADTO:  d.append(String.format(Locale.US,"Q%.2f %.2f %.2f %.2f ", c[0],c[1],c[2],c[3])); break;
        case PathIterator.SEG_CUBICTO: d.append(String.format(Locale.US,"C%.2f %.2f %.2f %.2f %.2f %.2f ", c[0],c[1],c[2],c[3],c[4],c[5])); break;
        case PathIterator.SEG_CLOSE:   d.append("Z "); break;
      }
      pi.next();
    }
    return d.toString().trim();
  }
  public static void main(String[] args) throws Exception {
    Class<?> cls = Class.forName(args[0]);
    for (String m : args[1].split(",")) {
      try {
        Shape s = (Shape)cls.getMethod(m).invoke(null);
        Rectangle2D b = s.getBounds2D();
        System.out.println(String.format(Locale.US,"### %s bbox=%.1f,%.1f,%.1f,%.1f", m,b.getX(),b.getY(),b.getWidth(),b.getHeight()));
        System.out.println(pathToSVG(s));
      } catch (Throwable e) { System.out.println("### "+m+" ERR "+e); }
    }
  }
}

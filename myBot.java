package myBot;

import ai.core.AI;
import ai.core.AIWithComputationBudget;
import ai.core.ParameterSpecification;
import ai.obiBotKenobi.ObiBotKenobi;
import ai.tma.TMA;
import rts.GameState;
import rts.PhysicalGameState;
import rts.PlayerAction;
import rts.units.UnitTypeTable;
import abid.Aggrobot;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

import static tests.RunExperimenter.loadAIFromJar;

public class myBot extends AIWithComputationBudget {
    /**
     * Constructs the controller with the specified time and iterations budget
     *
     * @param timeBudget       time in milisseconds
     * @param iterationsBudget number of allowed iterations
     */
    // UTT is a class that defines the game characteristics, workers, bases, units
    // constructor receives the unit time table, so how they behave what hitpoints they have,
    // how much dmg they do, actions they can do

    UnitTypeTable unitTypeTable = null;
    Aggrobot aggrobot;
    TMA tma;
    AI obiBotKenobi;
    // Cluster data:
    double[][] centroids;      // [k][nFeatures]
    String[] featureNames;     // same order as in your analysis CSV
    int k;                     // number of clusters
    String featureCsv = "C:/Users/bikep/IdeaProjects/myMicroRTSBot/single_trace_features.csv";
    Map<Integer, AI> clusterToAI = null;
    int currentClusterId;
    public static String nameOfOpponent;
    public static int currentIteration = 0;
    public static String pythonScript = "C:/Users/bikep/IdeaProjects/myMicroRTSBot/analyze_trace.py";
    public static String outputFolder = "C:/Users/bikep/IdeaProjects/myMicroRTSBot/traces/outputFolder";
    public static String singleTraceOutput = "";
    public static String getTraceFile() {
        return "C:/Users/bikep/IdeaProjects/myMicroRTSBot/traces/myBotTest/" + nameOfOpponent + "VsmyBot-" + currentIteration + "-0.xml";
    }
    public static boolean hasScriptBeenRun;
    private static final double[] MEAN = {
            151.97272727272727, 0.4763636363636364, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.09090909090909091, 0.04, 0.026363636363636363, 0.14909090909090908,
            0.11727272727272728, 0.03, 8.88256, 8.255275454545455, 8.089935454545454,
            8.036543636363637, 1.3963636363636365, 346.64272727272726, 15.18,
            0.12849636363636363, 251.68454545454546, 0.5636363636363636, 0.5,
            0.12545454545454546, 724.2036363636364, 0.5527272727272727, 2.3945454545454545,
            3.640909090909091, 5.2, 6.42, 8.796363636363637, 31.151136363636365
    };

    private static final double[] SCALE = {
            207.95600317422517, 0.5546378462527308, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
            0.28747978728803447, 0.19595917942265426, 0.16021421610244926,
            0.45880188922204646, 0.4551441511731283, 0.17583566708202808,
            1.6798292497209892, 1.8009712807606881, 1.7612012477070282,
            1.7713258703595336, 0.6113959099288169, 287.39419648695093,
            12.170245384842193, 0.13507660225844426, 135.05473482081499,
            1.7864503795733273, 1.4042144358388364, 0.5365608266181543,
            762.2658617482334, 0.4907710243556637, 0.6720168238744086,
            1.4087902905133283, 2.581049821645871, 4.602366979955186,
            8.648194002456943, 13.23327198182828
    };

    public myBot(UnitTypeTable utt) throws Exception {
        hasScriptBeenRun = false;
        currentClusterId = -1;
        super(-1, -1); //computation per frame
        unitTypeTable = utt;
        // Initialise our contenders
        aggrobot = new Aggrobot(utt);
        tma = new TMA(utt);
        obiBotKenobi = loadAIFromJar("C:/Users/bikep/IdeaProjects/MicroRTS/lib/bots/JannisRömermannMicroRTS.jar", utt);
        //Initialise our cluster data
        k = 6;
        featureNames = new String[]{
                "FirstBarracks",
                "NumBarracks",
                "Light100",
                "Heavy100",
                "Ranged100",
                "Light200",
                "Heavy200",
                "Ranged200",
                "Light400",
                "Heavy400",
                "Ranged400",
                "Light800",
                "Heavy800",
                "Ranged800",
                "AvgDist100",
                "AvgDist200",
                "AvgDist400",
                "AvgDist800",
                "MaxAttacksSingleTrace",
                "TimeMaxAttacks",
                "TotalAttacks",
                "AvgAttacksPerTrace",
                "FirstAttackTime",
                "TotalLight",
                "TotalHeavy",
                "TotalRanged",
                "GameLength",
                "PlayerWin",
                "Workers100",
                "Workers200",
                "Workers400",
                "Workers800",
                "TotalWorkers",
                "PercentMapHarvested"
        };
     //   System.out.println("feature names length " + featureNames.length);
        loadCentroids();
        loadClustersToBots();
     //   System.out.println(Arrays.deepToString(centroids));
    }

    @Override
    public void reset() {
    }

    private void loadClustersToBots() {
        clusterToAI = new HashMap<>();
        clusterToAI.put(0, tma);
        clusterToAI.put(1, aggrobot);
        clusterToAI.put(2, aggrobot);
        clusterToAI.put(3, tma);
        clusterToAI.put(4, tma);
        clusterToAI.put(5, obiBotKenobi);
    }

    private void loadCentroids() throws IOException {
        Path path = Paths.get("C:/Users/bikep/IdeaProjects/myMicroRTSBot/pythonCode/centroids.txt");

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String header = br.readLine();   // discard it, just to skip first line

            List<double[]> rows = new ArrayList<>();
            String line;
            while ((line = br.readLine()) != null) {
                String[] parts = line.split(",");
                int offset = 1; // skip cluster id column
                double[] vals = new double[parts.length - offset];
                for (int i = offset; i < parts.length; i++) {
                    vals[i - offset] = Double.parseDouble(parts[i]);
                }
                rows.add(vals);
            }
            centroids = rows.toArray(new double[0][]);
            k = centroids.length;
        }
    }

    public void tracesToClusterID(GameState gs) throws IOException {
        double[] analyzedTraceValues = loadFeatureRowNoHeader("single_trace_features.csv", featureNames.length);
        double[] xScaled = standardize(analyzedTraceValues);
      //  System.out.println(Arrays.toString(xScaled));

        int clusterId = assignCluster(xScaled);
        if (clusterId != currentClusterId) {
            currentClusterId = clusterId;
            //System.out.println("Assigned cluster: " + clusterId + " at time : " + gs.getTime() + " Swapping to bot: " + clusterToAI.get(currentClusterId).toString()) ;
            singleTraceOutput += "Assigned cluster: " + clusterId + " at time : " + gs.getTime() + " Swapping to bot: " + clusterToAI.get(currentClusterId).toString() + "\n";
        }
    }

    @Override
    public PlayerAction getAction(int player, GameState gs) throws Exception {
        if (hasScriptBeenRun) {
            tracesToClusterID(gs);
        }

        // readFile();
        //At every call to getAction, run our clustering script to open the file with traces, create a temp file with
        // essential traces cut out for us, and then run it into our script with set clusters to see which cluster it belongs too.
     //   System.out.println(gs.getPhysicalGameState());
        // Set previous frameGamestate for next turn
        if (clusterToAI.containsKey(currentClusterId)){
            return clusterToAI.get(currentClusterId).getAction(player, gs);
        }
        return aggrobot.getAction(player, gs);
    }

    private int assignCluster(double[] x) {
        int bestCluster = -1;
        double bestDist2 = Double.POSITIVE_INFINITY;

        for (int c = 0; c < centroids.length; c++) {
            double[] center = centroids[c];
            double dist2 = 0.0;
            for (int i = 0; i < center.length; i++) {
           //     System.out.print(x[i]+ " + " + center[i]);
                double d = x[i] - center[i];
                dist2 += d * d;          // squared Euclidean distance
            }
            if (dist2 < bestDist2) {
                bestDist2 = dist2;
                bestCluster = c;
            }
        }
      //  System.out.println("Nearest centroid = cluster " + bestCluster + ", squared distance = " + bestDist2);
        return bestCluster;
    }


    public static String callPythonScript(String scriptPath, String traceFilePath) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "python",
                    scriptPath,
                    traceFilePath,
                    "0",
                    "1"
            );
            pb.redirectErrorStream(true);  // merge stderr into stdout

            Process process = pb.start();

            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream())
            );
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[PYTHON] " + line);  // stream it to Java console
                output.append(line).append('\n');
            }

            // int exitCode = process.waitFor();
          //  System.out.println("Python exit code: " + exitCode);
            return output.toString().trim();

        } catch (Exception e) {
            System.out.println("bah  " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    private double[] loadFeatureRowNoHeader(String csvPath, int expectedCols) throws IOException {
        try (BufferedReader br = Files.newBufferedReader(Paths.get(csvPath))) {
            String row = br.readLine();
           // row = br.readLine();
            if (row == null) throw new IOException("Empty feature file");

            String[] vals = row.split(",");
            // System.out.println("vals.length = " + vals.length + ", expectedCols = " + expectedCols);

            if (vals.length != expectedCols) {
                throw new IOException("Column count mismatch: got " + vals.length +
                        ", expected " + expectedCols);
            }

            double[] feat = new double[expectedCols];
            for (int i = 0; i < expectedCols; i++) {
                feat[i] = Double.parseDouble(vals[i]);
            }
            return feat;
        }
    }

    private static double[] standardize(double[] x) {
        double[] z = new double[x.length];
        for (int i = 0; i < x.length; i++) {
            z[i] = (x[i] - MEAN[i]) / SCALE[i];
        }
        return z;
    }

    @Override
    public AI clone() {
        try {
            return new myBot(unitTypeTable);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public List<ParameterSpecification> getParameters() {
        return new ArrayList<>();
    }


    public void readFile() {
        String traceFile = "C:/Users/bikep/IdeaProjects/myMicroRTSBot/traces/myBotTest/RandomBiasedAIVsmyBot-0-0.xml";

        try (BufferedReader br = new BufferedReader(new FileReader(traceFile))) {
            String line;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
            }
        } catch (IOException e) {
            System.out.println("Cannot read file: " + traceFile);
            e.printStackTrace();
        }
    }
}

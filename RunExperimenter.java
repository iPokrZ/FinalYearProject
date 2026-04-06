package tests;

import abid.Aggrobot;
import ai.RandomBiasedAI;
import ai.coac.CoacAI;
import ai.competition.tiamat.Tiamat;
import ai.tma.TMA;
import ai.testTsune.TsuneBot;
import mayariBot.mayari;
import ai.core.AI;
import myBot.myBot;
import rts.units.UnitTypeTable;
import rts.PhysicalGameState;
import tournaments.LoadTournamentAIs;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.lang.reflect.Constructor;
import java.util.*;


public class RunExperimenter {
    public static void main(String[] args) throws Exception {
        UnitTypeTable utt = new UnitTypeTable();

        // 2020 Winner
        AI coac = new CoacAI(utt);
        // 2019 - 2021 winner
        // Note 2021 winner DOES not have public source code
        // no competition in 2020
        AI mayari = new mayari(utt);
        // 2018 winner
        AI tiamat = new Tiamat(utt);
        // 2024 winner
        AI TMA = new TMA(utt);
        // Best performing MCTS algorithm
        AI tsuneBot = new TsuneBot(utt);
        AI aggroBot = new Aggrobot(utt);
        // 2023 Second place - ObiBotKenobi does NOT work
        AI obiBotKenobi = loadAIFromJar("C:/Users/bikep/IdeaProjects/MicroRTS/lib/bots/JannisRömermannMicroRTS.jar", utt);
        // My bot :D
        AI myBot = new myBot(utt);
        List<AI> bots = new ArrayList<>();
       bots.add(aggroBot);
        bots.add(tiamat);
        bots.add(coac);
          bots.add(TMA);
        bots.add(mayari);
        bots.add(tsuneBot);
        bots.add(obiBotKenobi);
        bots.add(new ai.abstraction.WorkerRushPlusPlus(utt));
       bots.add(new ai.abstraction.partialobservability.POLightRush(utt));
        bots.add(new ai.abstraction.WorkerDefense(utt));
       // bots.add(myBot);
        bots.add(new RandomBiasedAI(utt));


        String mapPath = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/bases8x8.xml";
        String mapPath2 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8A.xml";
        String mapPath3 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8B.xml";
        String mapPath4 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8C.xml";
        String mapPath5 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8D.xml";
        String mapPath6 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8E.xml";
        String mapPath7 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8F.xml";
        String mapPath8 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8G.xml";
        String mapPath9 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8H.xml";
        String mapPath10 = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/8x8/basesWorkers8x8I.xml";

        String mapPath12x12A = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12.xml";
        String mapPath12x12B = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12A.xml";
        String mapPath12x12C = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12B.xml";
        String mapPath12x12D = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12C.xml";
        String mapPath12x12E = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12D.xml";
        String mapPath12x12F = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12E.xml";
        String mapPath12x12G = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12F.xml";
        String mapPath12x12H = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12G.xml";
        String mapPath12x12I = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12H.xml";
        String mapPath12x12J = "C:/Users/bikep/IdeaProjects/MicroRTS/maps/12x12/basesWorkers12x12I.xml";


        List<PhysicalGameState> maps8x8 = List.of(
                PhysicalGameState.load(mapPath, utt),
                PhysicalGameState.load(mapPath2, utt),
                PhysicalGameState.load(mapPath3, utt),
                PhysicalGameState.load(mapPath4, utt),
                PhysicalGameState.load(mapPath5, utt),
                PhysicalGameState.load(mapPath6, utt),
                PhysicalGameState.load(mapPath7, utt),
                PhysicalGameState.load(mapPath8, utt),
                PhysicalGameState.load(mapPath9, utt),
                PhysicalGameState.load(mapPath10, utt)
        );

        List<PhysicalGameState> maps12x12 = List.of(
                PhysicalGameState.load(mapPath12x12A, utt),
                PhysicalGameState.load(mapPath12x12B, utt),
                PhysicalGameState.load(mapPath12x12C, utt),
                PhysicalGameState.load(mapPath12x12D, utt),
                PhysicalGameState.load(mapPath12x12E, utt),
                PhysicalGameState.load(mapPath12x12F, utt),
                PhysicalGameState.load(mapPath12x12G, utt),
                PhysicalGameState.load(mapPath12x12H, utt),
                PhysicalGameState.load(mapPath12x12I, utt),
                PhysicalGameState.load(mapPath12x12J, utt)
        );

        int iterations = 1;       // games per pairing per map
        int maxCycles = 5000;
        int maxInactive = 400;

        try (PrintStream out = new PrintStream(new FileOutputStream("8x8-newIterations.txt"))) {
            // run_only_those_involving_this_AI = -1 (all pairs)
            // skip_self_play = true
            // partiallyObservable = false
            // bots -> list of ai's to evaluate, every ordered pair will be played
            // maps - list of maps to be played, every map will be played by a bot pair
            // utt -> unit type definitions, shared by environment and bots. Used when constructing gamestate
            // iterations -> number of games per bot-pair per length
            // maxCycles -> hard limit on game-length cycle -> if time greater than cycle, END GAME
            // max Inactive -> if no actions are issued, the loop stops
            // out -> where logs are printed
            // run only those involving this AI -> -1, run all pairs!
                // 0 or greater -> only run games where one the players has index 0 or greater, so only testing one bot
            // Self-play -> skip playing against each other
            // False ->
            Experimenter.runExperiments(
                    bots,
                    maps8x8,
                    utt,
                    iterations,
                    maxCycles,
                    maxInactive,
                    false,        // visualize
                    out,
                    -1,           // run_only_those_involving_this_AI
                    true,         // skip_self_play (no self-play)
                    false,         // partiallyObservable
                    false,
                    false,
                    "traces"
            );

            // java
            //Experimenter.runExperiments(
            //    bots,
            //    maps,
            //    utt,
            //    iterations,
            //    maxCycles,
            //    maxInactive,
            //    false,          // visualize
            //    out,
            //    -1,             // run_only_those_involving_this_AI
            //    true,           // skip_self_play
            //    false,          // partiallyObservable
            //    true,           // saveTrace  <-- enable
            //    false,          // saveZip (true = .zip, false = plain .xml)
            //    "traces"        // traceDir (must exist or be creatable)
            //);

            // explained statistic
            // Wins:
            //0, 4, 2,
            //0, 0, 0,
            //2, 0, 0,
            // this means that bot 0 beat bot 1, 4 times, so WORKER RUSH always BEATS MonteCarlo
            // Worker rush lost to
        }
    }

    private static List<AI> loadAIsFromJar(String jarPath, UnitTypeTable utt) throws Exception {
        List<Class> classes = LoadTournamentAIs.loadTournamentAIsFromJAR(jarPath);
        if (classes.isEmpty()) throw new Exception("No AI found in JAR: " + jarPath);

        List<AI> ais = new ArrayList<>();
        for (Class c : classes) {
            try {
                Constructor cons = c.getConstructor(UnitTypeTable.class);
                ais.add((AI) cons.newInstance(utt));
            } catch (Exception e) {
                System.err.println("Failed to instantiate " + c.getName() + ": " + e.getMessage());
            }
        }

        if (ais.isEmpty()) throw new Exception("No AI could be instantiated from JAR: " + jarPath);
        return ais;
    }

    public static AI loadAIFromJar(String jarPath, UnitTypeTable utt) throws Exception {
        List<Class> classes = LoadTournamentAIs.loadTournamentAIsFromJAR(jarPath);
        if (classes.isEmpty()) throw new Exception("No AI found in JAR: " + jarPath);
        Constructor cons = classes.get(0).getConstructor(UnitTypeTable.class);
        return (AI) cons.newInstance(utt);
    }

}

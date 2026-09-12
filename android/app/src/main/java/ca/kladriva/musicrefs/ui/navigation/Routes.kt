package ca.kladriva.musicrefs.ui.navigation

sealed class Routes(val route: String) {
    data object Home : Routes("home")
    data object SoloSetup : Routes("solo/setup")
    data object SoloPlay : Routes("solo/play")
    data object PartyHub : Routes("party/hub")
    data object PartyLobby : Routes("party/lobby")
    data object PartyPlay : Routes("party/play")
    data object PartyResults : Routes("party/results")
}

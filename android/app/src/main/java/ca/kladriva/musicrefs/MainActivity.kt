package ca.kladriva.musicrefs

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import ca.kladriva.musicrefs.ui.home.HomeScreen
import ca.kladriva.musicrefs.ui.navigation.Routes
import ca.kladriva.musicrefs.ui.party.PartyHubScreen
import ca.kladriva.musicrefs.ui.party.PartyLobbyScreen
import ca.kladriva.musicrefs.ui.party.PartyNav
import ca.kladriva.musicrefs.ui.party.PartyPlayScreen
import ca.kladriva.musicrefs.ui.party.PartyResultsScreen
import ca.kladriva.musicrefs.ui.party.PartyViewModel
import ca.kladriva.musicrefs.ui.solo.SoloPlayScreen
import ca.kladriva.musicrefs.ui.solo.SoloSetupScreen
import ca.kladriva.musicrefs.ui.solo.SoloViewModel
import ca.kladriva.musicrefs.ui.theme.BgDark
import ca.kladriva.musicrefs.ui.theme.MusicRefsTheme
import ca.kladriva.musicrefs.ui.theme.NeonCyan
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val deepLinkCodeState = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        deepLinkCodeState.value = extractPartyCode(intent)
        setContent {
            val deepLinkCode by deepLinkCodeState
            MusicRefsTheme {
                MusicRefsAppNav(
                    deepLinkCode = deepLinkCode,
                    onDeepLinkConsumed = { deepLinkCodeState.value = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        deepLinkCodeState.value = extractPartyCode(intent)
    }

    private fun extractPartyCode(intent: Intent?): String? {
        val data: Uri = intent?.data ?: return null
        return data.getQueryParameter("code")?.takeIf { it.isNotBlank() }?.uppercase()
    }
}

@Composable
private fun MusicRefsAppNav(
    deepLinkCode: String?,
    onDeepLinkConsumed: () -> Unit,
) {
    val navController = rememberNavController()
    val partyVm: PartyViewModel = hiltViewModel()
    val backStack by navController.currentBackStackEntryAsState()
    val route = backStack?.destination?.route
    var confirmLeave by remember { mutableStateOf(false) }

    val inActiveGame = route in setOf(
        Routes.SoloPlay.route,
        Routes.PartyLobby.route,
        Routes.PartyPlay.route,
    )

    BackHandler(enabled = inActiveGame) {
        confirmLeave = true
    }

    if (confirmLeave) {
        AlertDialog(
            onDismissRequest = { confirmLeave = false },
            title = { Text("Quitter ?") },
            text = { Text("Une partie est en cours. Revenir à l'accueil ?") },
            confirmButton = {
                TextButton(onClick = {
                    confirmLeave = false
                    partyVm.leave()
                    navController.navigate(Routes.Home.route) {
                        popUpTo(Routes.Home.route) { inclusive = true }
                    }
                }) { Text("Accueil", color = NeonCyan) }
            },
            dismissButton = {
                TextButton(onClick = { confirmLeave = false }) { Text("Rester") }
            },
        )
    }

    LaunchedEffect(deepLinkCode) {
        if (!deepLinkCode.isNullOrBlank()) {
            partyVm.setDeepLinkCode(deepLinkCode)
            navController.navigate(Routes.PartyHub.route) {
                launchSingleTop = true
            }
            onDeepLinkConsumed()
        }
    }

    LaunchedEffect(Unit) {
        partyVm.navEvents.collect { event ->
            when (event) {
                PartyNav.Lobby -> navController.navigate(Routes.PartyLobby.route) {
                    launchSingleTop = true
                }
                PartyNav.Play -> navController.navigate(Routes.PartyPlay.route) {
                    popUpTo(Routes.PartyLobby.route) { inclusive = true }
                    launchSingleTop = true
                }
                PartyNav.Results -> navController.navigate(Routes.PartyResults.route) {
                    popUpTo(Routes.PartyPlay.route) { inclusive = true }
                    launchSingleTop = true
                }
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = Routes.Home.route,
        modifier = Modifier
            .fillMaxSize()
            .background(BgDark)
            .safeDrawingPadding(),
    ) {
        composable(Routes.Home.route) {
            HomeScreen(
                onSolo = { navController.navigate(Routes.SoloSetup.route) },
                onParty = { navController.navigate(Routes.PartyHub.route) },
            )
        }
        composable(Routes.SoloSetup.route) {
            val soloVm: SoloViewModel = hiltViewModel()
            SoloSetupScreen(
                vm = soloVm,
                onHome = { navController.popBackStack(Routes.Home.route, inclusive = false) },
                onStarted = {
                    navController.navigate(Routes.SoloPlay.route) {
                        // keep setup in back stack so VM is shared
                    }
                },
            )
        }
        composable(Routes.SoloPlay.route) { entry ->
            val parentEntry = remember(entry) {
                navController.getBackStackEntry(Routes.SoloSetup.route)
            }
            val soloVm: SoloViewModel = hiltViewModel(parentEntry)
            SoloPlayScreen(
                vm = soloVm,
                onHome = {
                    navController.popBackStack(Routes.Home.route, inclusive = false)
                },
            )
        }
        composable(Routes.PartyHub.route) {
            PartyHubScreen(
                vm = partyVm,
                onHome = { navController.popBackStack(Routes.Home.route, inclusive = false) },
            )
        }
        composable(Routes.PartyLobby.route) {
            PartyLobbyScreen(
                vm = partyVm,
                onHome = {
                    partyVm.leave()
                    navController.popBackStack(Routes.Home.route, inclusive = false)
                },
            )
        }
        composable(Routes.PartyPlay.route) {
            PartyPlayScreen(
                vm = partyVm,
                onHome = {
                    partyVm.leave()
                    navController.popBackStack(Routes.Home.route, inclusive = false)
                },
            )
        }
        composable(Routes.PartyResults.route) {
            PartyResultsScreen(
                vm = partyVm,
                onHome = {
                    partyVm.leave()
                    navController.popBackStack(Routes.Home.route, inclusive = false)
                },
                onNewParty = {
                    navController.navigate(Routes.PartyHub.route) {
                        popUpTo(Routes.Home.route)
                    }
                },
            )
        }
    }
}

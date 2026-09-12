package ca.kladriva.musicrefs.ui.party

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ca.kladriva.musicrefs.data.model.GameMode
import ca.kladriva.musicrefs.data.model.PartyPlayerDto
import ca.kladriva.musicrefs.ui.components.AppTextField
import ca.kladriva.musicrefs.ui.components.GameTopBar
import ca.kladriva.musicrefs.ui.components.ModeToggle
import ca.kladriva.musicrefs.ui.components.PrimaryButton
import ca.kladriva.musicrefs.ui.components.ScoreHud
import ca.kladriva.musicrefs.ui.components.ScreenScaffold
import ca.kladriva.musicrefs.ui.components.SecondaryButton
import ca.kladriva.musicrefs.ui.solo.EasyQuiz
import ca.kladriva.musicrefs.ui.theme.Muted
import ca.kladriva.musicrefs.ui.theme.NeonCyan
import ca.kladriva.musicrefs.ui.theme.NeonPink
import ca.kladriva.musicrefs.ui.theme.OnDark
import ca.kladriva.musicrefs.ui.theme.QuoteStyle
import ca.kladriva.musicrefs.ui.theme.SurfaceDark

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PartyHubScreen(
    vm: PartyViewModel,
    onHome: () -> Unit,
) {
    val state by vm.hub.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var expanded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        vm.messages.collect { snackbar.showSnackbar(it) }
    }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = { GameTopBar(title = "Partie amis", onHome = onHome) },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
        ) {
            if (state.deepLinkCode != null) {
                Text("Code reçu : ${state.deepLinkCode}", color = NeonCyan, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                AppTextField(
                    value = state.joinName,
                    onValueChange = { vm.updateHub(joinName = it) },
                    label = "Ton prénom",
                    imeAction = ImeAction.Done,
                    onDone = { vm.joinParty() },
                )
                Spacer(Modifier.height(12.dp))
                PrimaryButton(text = "Rejoindre", onClick = vm::joinParty, enabled = !state.loading)
                Spacer(Modifier.height(24.dp))
            }

            Text("Créer un salon", color = OnDark, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Spacer(Modifier.height(10.dp))
            AppTextField(
                value = state.hostName,
                onValueChange = { vm.updateHub(hostName = it) },
                label = "Prénom (hôte)",
            )
            Spacer(Modifier.height(10.dp))
            Text("Catégorie", color = Muted)
            ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
                val label = state.categories.firstOrNull { it.id == state.selectedCategoryId }?.name ?: "—"
                OutlinedTextField(
                    value = label,
                    onValueChange = {},
                    readOnly = true,
                    modifier = Modifier.menuAnchor().fillMaxWidth(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                )
                ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    state.categories.forEach { cat ->
                        DropdownMenuItem(
                            text = { Text("${cat.name} (${cat.quoteCount})") },
                            onClick = {
                                vm.updateHub(categoryId = cat.id)
                                expanded = false
                            },
                        )
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
            ModeToggle(
                selectedEasy = state.mode == GameMode.EASY,
                onSelect = { easy -> vm.updateHub(mode = if (easy) GameMode.EASY else GameMode.CLASSIC) },
            )
            Spacer(Modifier.height(8.dp))
            AppTextField(
                value = state.roundLimit.toString(),
                onValueChange = { v ->
                    v.toIntOrNull()?.let { vm.updateHub(rounds = it.coerceIn(3, 30)) }
                },
                label = "Rounds (3–30)",
            )
            Spacer(Modifier.height(12.dp))
            if (state.loading) {
                CircularProgressIndicator(color = NeonPink, modifier = Modifier.align(Alignment.CenterHorizontally))
            } else {
                PrimaryButton(text = "Créer la partie", onClick = vm::createParty)
            }

            Spacer(Modifier.height(28.dp))
            Text("Rejoindre", color = OnDark, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Spacer(Modifier.height(10.dp))
            AppTextField(
                value = state.joinName,
                onValueChange = { vm.updateHub(joinName = it) },
                label = "Prénom",
            )
            Spacer(Modifier.height(10.dp))
            AppTextField(
                value = state.joinCode,
                onValueChange = { vm.updateHub(joinCode = it.uppercase()) },
                label = "Code salon",
                imeAction = ImeAction.Done,
                onDone = { vm.joinParty() },
            )
            Spacer(Modifier.height(12.dp))
            SecondaryButton(text = "Rejoindre le salon", onClick = vm::joinParty, enabled = !state.loading)
        }
    }
}

@Composable
fun PartyLobbyScreen(
    vm: PartyViewModel,
    onHome: () -> Unit,
) {
    val state by vm.session.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val snap = state.snapshot

    LaunchedEffect(Unit) {
        vm.messages.collect { snackbar.showSnackbar(it) }
    }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = {
            GameTopBar(title = "Lobby", onHome = {
                vm.leave()
                onHome()
            })
        },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(snap?.code.orEmpty(), color = NeonPink, fontWeight = FontWeight.Black, fontSize = 42.sp, letterSpacing = 6.sp)
            Spacer(Modifier.height(8.dp))
            val modeLabel = if (state.mode == GameMode.EASY) "Facile (quiz)" else "Normal"
            Text(
                "${snap?.category?.name.orEmpty()} · ${snap?.roundLimit ?: 0} punchlines · $modeLabel",
                color = Muted,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(20.dp))
            Text("Joueurs", color = OnDark, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            snap?.players.orEmpty().forEach { p ->
                Text(
                    "${p.name}${if (p.isHost) " (hôte)" else ""}",
                    color = if (p.name == state.myName) NeonCyan else OnDark,
                    modifier = Modifier.padding(vertical = 4.dp),
                )
            }
            Spacer(Modifier.height(20.dp))
            SecondaryButton(text = "Partager le lien", onClick = vm::shareInvite)
            Spacer(Modifier.height(12.dp))
            if (state.hostToken != null) {
                PrimaryButton(text = "Lancer la partie", onClick = vm::startParty)
            } else {
                Text("En attente que l'hôte lance…", color = Muted)
            }
            Spacer(Modifier.height(12.dp))
            SecondaryButton(text = "Quitter", onClick = {
                vm.leave()
                onHome()
            })
        }
    }
}

@Composable
fun PartyPlayScreen(
    vm: PartyViewModel,
    onHome: () -> Unit,
) {
    val state by vm.session.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val players = vm.rankedPlayers()

    LaunchedEffect(Unit) {
        vm.messages.collect { snackbar.showSnackbar(it) }
    }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = {
            GameTopBar(title = "Partie", onHome = {
                vm.leave()
                onHome()
            })
        },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
        ) {
            ScoreHud(
                score = state.score,
                streak = state.streak,
                highScore = state.highScore,
                progress = state.progressLabel,
            )
            Spacer(Modifier.height(12.dp))
            LiveBoard(players = players, me = state.myName)
            Spacer(Modifier.height(16.dp))

            if (state.locallyFinished || state.waitingOthers) {
                Text(
                    "Terminé de ton côté — en attente des autres…",
                    color = NeonCyan,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
            } else {
                Text(
                    text = "« ${state.quote?.quote.orEmpty()} »",
                    style = QuoteStyle,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(12.dp))
                if (state.revealedHints.isNotEmpty()) {
                    state.revealedHints.forEach { (k, v) ->
                        Text("$k : $v", color = NeonCyan, fontSize = 14.sp)
                    }
                }
                Row(Modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("year" to "Année", "genre" to "Genre", "album" to "Album", "initials" to "Init.").forEach { (key, label) ->
                        TextButton(
                            onClick = { vm.revealHint(key) },
                            enabled = key !in state.revealedHints,
                            modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        ) {
                            Text(label, fontSize = 11.sp, color = if (key in state.revealedHints) Muted else NeonPink)
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                if (state.mode == GameMode.EASY) {
                    EasyQuiz(
                        artists = state.quiz?.artists.orEmpty(),
                        titles = state.quiz?.titles.orEmpty(),
                        selectedArtist = state.selectedArtist,
                        selectedTitle = state.selectedTitle,
                        artistLocked = state.artistGuessed,
                        titleLocked = state.titleGuessed,
                        onArtist = vm::selectQuizArtist,
                        onTitle = vm::selectQuizTitle,
                    )
                } else {
                    AppTextField(value = state.artistInput, onValueChange = vm::onArtistChange, label = "Artiste")
                    Spacer(Modifier.height(8.dp))
                    AppTextField(
                        value = state.titleInput,
                        onValueChange = vm::onTitleChange,
                        label = "Titre",
                        imeAction = ImeAction.Done,
                        onDone = { vm.validate() },
                    )
                    Spacer(Modifier.height(10.dp))
                    PrimaryButton(text = "Valider", onClick = { vm.validate() })
                }
                state.feedback?.let {
                    Spacer(Modifier.height(8.dp))
                    Text(it, color = OnDark, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                }
                Spacer(Modifier.height(10.dp))
                SecondaryButton(
                    text = if (state.artistGuessed && state.titleGuessed) "Suivant" else "Passer",
                    onClick = vm::nextRound,
                )
            }
            Spacer(Modifier.height(12.dp))
            SecondaryButton(text = "Quitter", onClick = {
                vm.leave()
                onHome()
            })
        }
    }
}

@Composable
fun PartyResultsScreen(
    vm: PartyViewModel,
    onHome: () -> Unit,
    onNewParty: () -> Unit,
) {
    val state by vm.session.collectAsStateWithLifecycle()
    val players = vm.rankedPlayers()
    val snackbar = remember { SnackbarHostState() }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = { GameTopBar(title = "Résultats", onHome = onHome) },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
        ) {
            Text("Classement final", color = OnDark, fontWeight = FontWeight.Bold, fontSize = 22.sp)
            Spacer(Modifier.height(12.dp))
            players.forEachIndexed { index, p ->
                Text(
                    "${index + 1}. ${p.name} — ${p.score} pts",
                    color = if (p.name == state.myName) NeonCyan else OnDark,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(vertical = 6.dp),
                )
            }
            Spacer(Modifier.height(24.dp))
            PrimaryButton(text = "Nouvelle partie", onClick = {
                vm.leave()
                onNewParty()
            })
            Spacer(Modifier.height(10.dp))
            SecondaryButton(text = "Accueil", onClick = {
                vm.leave()
                onHome()
            })
        }
    }
}

@Composable
private fun LiveBoard(players: List<PartyPlayerDto>, me: String?) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(SurfaceDark)
            .padding(12.dp),
    ) {
        Text("Classement live", color = Muted, fontSize = 13.sp)
        Spacer(Modifier.height(8.dp))
        players.forEach { p ->
            val total = (p.total.takeIf { it > 0 } ?: 1).toFloat()
            val prog = (p.progress.coerceAtLeast(0) / total).coerceIn(0f, 1f)
            val highlight = p.name == me
            Text(
                "${p.name} — ${p.score} pts${if (p.finished) " ✓" else ""}",
                color = if (highlight) NeonCyan else OnDark,
                fontWeight = if (highlight) FontWeight.Bold else FontWeight.Normal,
            )
            LinearProgressIndicator(
                progress = { prog },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp)
                    .height(6.dp),
                color = if (highlight) NeonPink else NeonCyan,
                trackColor = Color.White.copy(alpha = 0.1f),
            )
        }
    }
}

package ca.kladriva.musicrefs.ui.solo

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import ca.kladriva.musicrefs.ui.components.AppTextField
import ca.kladriva.musicrefs.ui.components.GameTopBar
import ca.kladriva.musicrefs.ui.components.ModeToggle
import ca.kladriva.musicrefs.ui.components.PrimaryButton
import ca.kladriva.musicrefs.ui.components.ScoreHud
import ca.kladriva.musicrefs.ui.components.ScreenScaffold
import ca.kladriva.musicrefs.ui.components.SecondaryButton
import ca.kladriva.musicrefs.ui.theme.Muted
import ca.kladriva.musicrefs.ui.theme.NeonCyan
import ca.kladriva.musicrefs.ui.theme.NeonPink
import ca.kladriva.musicrefs.ui.theme.OnDark
import ca.kladriva.musicrefs.ui.theme.QuoteStyle
import ca.kladriva.musicrefs.ui.theme.SurfaceDark

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SoloSetupScreen(
    vm: SoloViewModel,
    onHome: () -> Unit,
    onStarted: () -> Unit,
) {
    val state by vm.setup.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    var expanded by remember { mutableStateOf(false) }

    LaunchedEffect(state.error) {
        state.error?.let { snackbar.showSnackbar(it) }
    }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = { GameTopBar(title = "Solo", onHome = onHome) },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
        ) {
            Text("Prépare ta partie", color = OnDark, fontWeight = FontWeight.Bold, fontSize = 22.sp)
            Spacer(Modifier.height(16.dp))
            Text("Catégorie", color = Muted)
            Spacer(Modifier.height(8.dp))
            ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
                val label = state.categories.firstOrNull { it.id == state.selectedCategoryId }?.name
                    ?: "Toutes"
                OutlinedTextField(
                    value = label,
                    onValueChange = {},
                    readOnly = true,
                    modifier = Modifier
                        .menuAnchor()
                        .fillMaxWidth(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                )
                ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    DropdownMenuItem(
                        text = { Text("Toutes") },
                        onClick = {
                            vm.selectCategory(null)
                            expanded = false
                        },
                    )
                    state.categories.forEach { cat ->
                        DropdownMenuItem(
                            text = { Text("${cat.name} (${cat.quoteCount})") },
                            onClick = {
                                vm.selectCategory(cat.id)
                                expanded = false
                            },
                        )
                    }
                }
            }
            Spacer(Modifier.height(20.dp))
            Text("Mode", color = Muted)
            ModeToggle(
                selectedEasy = state.mode == GameMode.EASY,
                onSelect = { easy -> vm.setMode(if (easy) GameMode.EASY else GameMode.CLASSIC) },
            )
            Spacer(Modifier.height(28.dp))
            if (state.loading) {
                CircularProgressIndicator(color = NeonPink, modifier = Modifier.align(Alignment.CenterHorizontally))
            } else {
                PrimaryButton(text = "Commencer", onClick = { vm.startGame(onStarted) })
            }
        }
    }
}

@Composable
fun SoloPlayScreen(
    vm: SoloViewModel,
    onHome: () -> Unit,
) {
    val state by vm.play.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        vm.messages.collect { snackbar.showSnackbar(it) }
    }

    ScreenScaffold(
        snackbarHostState = snackbar,
        topBar = { GameTopBar(title = "Solo", onHome = onHome) },
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(bottom = 24.dp),
        ) {
            ScoreHud(score = state.score, streak = state.streak, highScore = state.highScore)
            Spacer(Modifier.height(20.dp))
            Text(
                text = "« ${state.quote?.quote.orEmpty()} »",
                style = QuoteStyle,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(16.dp))

            if (state.revealedHints.isNotEmpty()) {
                state.revealedHints.forEach { (k, v) ->
                    Text("$k : $v", color = NeonCyan, fontSize = 14.sp)
                }
                Spacer(Modifier.height(8.dp))
            }

            Row(Modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                listOf("year" to "Année", "genre" to "Genre", "album" to "Album", "initials" to "Initiales").forEach { (key, label) ->
                    TextButton(
                        onClick = { vm.revealHint(key) },
                        enabled = key !in state.revealedHints && !state.artistGuessed || key !in state.revealedHints,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                    ) {
                        Text(label, fontSize = 11.sp, color = if (key in state.revealedHints) Muted else NeonPink)
                    }
                }
            }

            Spacer(Modifier.height(12.dp))
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
                AppTextField(
                    value = state.artistInput,
                    onValueChange = vm::onArtistChange,
                    label = if (state.artistGuessed) "Artiste ✓" else "Artiste",
                    imeAction = ImeAction.Next,
                )
                Spacer(Modifier.height(10.dp))
                AppTextField(
                    value = state.titleInput,
                    onValueChange = vm::onTitleChange,
                    label = if (state.titleGuessed) "Titre ✓" else "Titre / moment",
                    imeAction = ImeAction.Done,
                    onDone = { vm.validate() },
                )
                Spacer(Modifier.height(12.dp))
                PrimaryButton(text = "Valider", onClick = { vm.validate() })
            }

            state.feedback?.let {
                Spacer(Modifier.height(10.dp))
                Text(it, color = OnDark, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
            }

            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = if (state.artistGuessed && state.titleGuessed) "Suivant" else "Passer",
                onClick = vm::next,
            )
            Spacer(Modifier.height(8.dp))
            SecondaryButton(text = "Reset", onClick = vm::reset)
        }
    }
}

@Composable
fun EasyQuiz(
    artists: List<String>,
    titles: List<String>,
    selectedArtist: String?,
    selectedTitle: String?,
    artistLocked: Boolean,
    titleLocked: Boolean,
    onArtist: (String) -> Unit,
    onTitle: (String) -> Unit,
) {
    Text("Artiste", color = Muted, fontWeight = FontWeight.SemiBold)
    Spacer(Modifier.height(6.dp))
    ChoiceGrid(
        options = artists,
        selected = selectedArtist,
        locked = artistLocked,
        accent = NeonPink,
        onSelect = onArtist,
    )
    Spacer(Modifier.height(14.dp))
    Text("Titre", color = Muted, fontWeight = FontWeight.SemiBold)
    Spacer(Modifier.height(6.dp))
    ChoiceGrid(
        options = titles,
        selected = selectedTitle,
        locked = titleLocked,
        accent = NeonCyan,
        onSelect = onTitle,
    )
}

@Composable
private fun ChoiceGrid(
    options: List<String>,
    selected: String?,
    locked: Boolean,
    accent: Color,
    onSelect: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        options.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                row.forEach { opt ->
                    val isSelected = selected == opt
                    Text(
                        text = opt,
                        color = if (isSelected) Color.White else OnDark,
                        fontWeight = FontWeight.SemiBold,
                        textAlign = TextAlign.Center,
                        modifier = Modifier
                            .weight(1f)
                            .heightIn(min = 52.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (isSelected) accent.copy(alpha = 0.85f) else SurfaceDark)
                            .then(
                                if (!locked) Modifier.clickable { onSelect(opt) } else Modifier,
                            )
                            .padding(12.dp),
                    )
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

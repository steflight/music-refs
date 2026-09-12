package ca.kladriva.musicrefs.ui.solo

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ca.kladriva.musicrefs.data.api.ApiResult
import ca.kladriva.musicrefs.data.model.CategoryDto
import ca.kladriva.musicrefs.data.model.GameMode
import ca.kladriva.musicrefs.data.prefs.UserPreferences
import ca.kladriva.musicrefs.data.repository.MusicRefsRepository
import ca.kladriva.musicrefs.domain.game.GameEngine
import ca.kladriva.musicrefs.domain.game.QuizChoices
import ca.kladriva.musicrefs.domain.game.Quote
import ca.kladriva.musicrefs.domain.game.buildQuizChoices
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SoloSetupState(
    val categories: List<CategoryDto> = emptyList(),
    val selectedCategoryId: Int? = null,
    val mode: GameMode = GameMode.CLASSIC,
    val loading: Boolean = false,
    val error: String? = null,
)

data class SoloPlayState(
    val quote: Quote? = null,
    val score: Int = 0,
    val streak: Int = 0,
    val highScore: Int = 0,
    val artistInput: String = "",
    val titleInput: String = "",
    val artistGuessed: Boolean = false,
    val titleGuessed: Boolean = false,
    val revealedHints: Map<String, String> = emptyMap(),
    val feedback: String? = null,
    val mode: GameMode = GameMode.CLASSIC,
    val quiz: QuizChoices? = null,
    val selectedArtist: String? = null,
    val selectedTitle: String? = null,
    val loading: Boolean = false,
)

@HiltViewModel
class SoloViewModel @Inject constructor(
    private val repository: MusicRefsRepository,
    private val prefs: UserPreferences,
) : ViewModel() {

    private val _setup = MutableStateFlow(SoloSetupState())
    val setup: StateFlow<SoloSetupState> = _setup.asStateFlow()

    private val _play = MutableStateFlow(SoloPlayState())
    val play: StateFlow<SoloPlayState> = _play.asStateFlow()

    private val _messages = MutableSharedFlow<String>()
    val messages: SharedFlow<String> = _messages.asSharedFlow()

    private var engine: GameEngine? = null
    private var pool: List<Quote> = emptyList()

    init {
        loadCategories()
    }

    fun loadCategories() {
        viewModelScope.launch {
            _setup.update { it.copy(loading = true, error = null) }
            when (val res = repository.categories()) {
                is ApiResult.Ok -> _setup.update {
                    it.copy(categories = res.value, loading = false)
                }
                is ApiResult.Err -> _setup.update {
                    it.copy(loading = false, error = res.message)
                }
            }
        }
    }

    fun selectCategory(id: Int?) {
        _setup.update { it.copy(selectedCategoryId = id) }
    }

    fun setMode(mode: GameMode) {
        _setup.update { it.copy(mode = mode) }
    }

    fun startGame(onReady: () -> Unit) {
        viewModelScope.launch {
            _setup.update { it.copy(loading = true, error = null) }
            val high = prefs.getHighScore()
            when (val res = repository.quotes(_setup.value.selectedCategoryId)) {
                is ApiResult.Ok -> {
                    if (res.value.isEmpty()) {
                        _setup.update { it.copy(loading = false, error = "Aucune punchline dans cette catégorie.") }
                        return@launch
                    }
                    pool = res.value
                    engine = GameEngine(
                        quotesList = pool,
                        highScoreProvider = { high },
                        highScoreSaver = { score -> viewModelScope.launch { prefs.saveHighScore(score) } },
                    )
                    syncPlayFromEngine(mode = _setup.value.mode, feedback = null)
                    _setup.update { it.copy(loading = false) }
                    onReady()
                }
                is ApiResult.Err -> {
                    _setup.update { it.copy(loading = false, error = res.message) }
                    _messages.emit(res.message)
                }
            }
        }
    }

    fun onArtistChange(v: String) = _play.update { it.copy(artistInput = v) }
    fun onTitleChange(v: String) = _play.update { it.copy(titleInput = v) }

    fun selectQuizArtist(v: String) {
        _play.update { it.copy(selectedArtist = v) }
        maybeAutoSubmitEasy()
    }

    fun selectQuizTitle(v: String) {
        _play.update { it.copy(selectedTitle = v) }
        maybeAutoSubmitEasy()
    }

    private fun maybeAutoSubmitEasy() {
        val s = _play.value
        if (s.mode != GameMode.EASY) return
        val a = s.selectedArtist ?: return
        val t = s.selectedTitle ?: return
        if (s.artistGuessed && s.titleGuessed) return
        validate(a, t)
    }

    fun validate(artist: String? = null, title: String? = null) {
        val e = engine ?: return
        val s = _play.value
        val a = artist ?: s.artistInput
        val t = title ?: s.titleInput
        val result = e.validateAnswer(a, t)
        syncPlayFromEngine(mode = s.mode, feedback = result.message)
        if (result.isFullyGuessed) {
            // keep quiz selections locked via guessed flags
        }
    }

    fun revealHint(type: String) {
        val e = engine ?: return
        val res = e.revealHint(type)
        if (res.success && res.value != null) {
            syncPlayFromEngine(
                mode = _play.value.mode,
                feedback = "Indice (−20 pts) : ${res.value}",
            )
        } else {
            viewModelScope.launch { _messages.emit(res.reason ?: "Indice indisponible") }
        }
    }

    fun next() {
        val e = engine ?: return
        if (_play.value.artistGuessed && _play.value.titleGuessed) {
            e.selectRandomQuote()
        } else {
            e.skipQuote()
        }
        syncPlayFromEngine(mode = _play.value.mode, feedback = null, clearInputs = true)
    }

    fun reset() {
        engine?.resetGame()
        syncPlayFromEngine(mode = _play.value.mode, feedback = "Partie remise à zéro", clearInputs = true)
    }

    private fun syncPlayFromEngine(mode: GameMode, feedback: String?, clearInputs: Boolean = false) {
        val e = engine ?: return
        val quiz = if (mode == GameMode.EASY) buildQuizChoices(e.currentQuote, pool) else null
        _play.update {
            it.copy(
                quote = e.currentQuote,
                score = e.score,
                streak = e.streak,
                highScore = e.highScore,
                artistGuessed = e.artistGuessed,
                titleGuessed = e.titleGuessed,
                revealedHints = e.revealedHints.associateWith { type ->
                    e.currentQuote?.hints?.get(type).orEmpty()
                }.filterValues { v -> v.isNotBlank() },
                feedback = feedback,
                mode = mode,
                quiz = quiz,
                artistInput = if (clearInputs) "" else it.artistInput,
                titleInput = if (clearInputs) "" else it.titleInput,
                selectedArtist = if (clearInputs) null else it.selectedArtist,
                selectedTitle = if (clearInputs) null else it.selectedTitle,
                loading = false,
            )
        }
        if (clearInputs) {
            _play.update { it.copy(selectedArtist = null, selectedTitle = null, artistInput = "", titleInput = "") }
        }
        // When moving to a new quote in easy, always reset selections
        if (clearInputs || (mode == GameMode.EASY && !e.artistGuessed && !e.titleGuessed)) {
            if (clearInputs) {
                _play.update { it.copy(quiz = quiz) }
            }
        }
    }
}

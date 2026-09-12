package ca.kladriva.musicrefs.domain.game

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class GameEngineTest {

    private val quotes = listOf(
        Quote(
            id = 101,
            quote = "Test quote 1",
            artist = "Artist One",
            title = "Song One",
            hints = Hints(year = "2020", genre = "Pop", album = "Album One", initials = "A.O - S.O"),
        ),
        Quote(
            id = 102,
            quote = "Test quote 2",
            artist = "Artist Two",
            title = "Song Two",
            hints = Hints(year = "2022", genre = "Rock", album = "Album Two", initials = "A.T - S.T"),
        ),
    )

    @Test
    fun normalize_stripsAccentsAndPunctuation() {
        assertThat(normalizeString("A l'ammoniaque!")).isEqualTo("alammoniaque")
        assertThat(normalizeString("  Ninho-- ")).isEqualTo("ninho")
        assertThat(normalizeString("Été indien")).isEqualTo("eteindien")
    }

    @Test
    fun isMatch_exactAndFuzzy() {
        assertThat(isMatch("Ninho", "Ninho")).isTrue()
        assertThat(isMatch("ninho", "Ninho")).isTrue()
        assertThat(isMatch("daft punk", "Daft Punk")).isTrue()
        assertThat(isMatch("orelsan", "OrelSan")).isTrue()
        assertThat(isMatch("pnl", "PNL")).isTrue()
    }

    @Test
    fun revealHint_tracksAndRejectsDuplicate() {
        val game = GameEngine(quotes)
        val res = game.revealHint("year")
        assertThat(res.success).isTrue()
        assertThat(res.value).isEqualTo(game.currentQuote!!.hints.year)
        assertThat(game.revealedHints).contains("year")
        assertThat(game.revealHint("year").success).isFalse()
    }

    @Test
    fun validate_fullGuessWithHintPenaltyAndStreak() {
        val game = GameEngine(quotes)
        val artist = game.currentQuote!!.artist
        val title = game.currentQuote!!.title
        game.revealHint("year")
        val validation = game.validateAnswer(artist, title)
        assertThat(validation.success).isTrue()
        assertThat(validation.isFullyGuessed).isTrue()
        assertThat(game.streak).isEqualTo(1)
        assertThat(game.score).isGreaterThan(0)
    }

    @Test
    fun skip_resetsStreak() {
        val game = GameEngine(quotes)
        // force streak via reflection-free path: full guess then skip
        game.validateAnswer(game.currentQuote!!.artist, game.currentQuote!!.title)
        assertThat(game.streak).isAtLeast(1)
        game.skipQuote()
        assertThat(game.streak).isEqualTo(0)
    }

    @Test
    fun reset_clearsScoreAndStreak() {
        val game = GameEngine(quotes)
        game.validateAnswer(game.currentQuote!!.artist, game.currentQuote!!.title)
        game.resetGame()
        assertThat(game.score).isEqualTo(0)
        assertThat(game.streak).isEqualTo(0)
    }

    @Test
    fun orderedMode_advancesThenFinishes() {
        val game = GameEngine(quotes)
        game.setQuotes(quotes, ordered = true)
        assertThat(game.orderIndex).isEqualTo(0)
        assertThat(game.advanceOrdered()).isNotNull()
        assertThat(game.orderIndex).isEqualTo(1)
        assertThat(game.advanceOrdered()).isNull()
    }

    @Test
    fun buildQuizChoices_includesCorrectAndSize() {
        val current = quotes.first()
        val quiz = buildQuizChoices(current, quotes, count = 4)
        assertThat(quiz.artists).hasSize(4)
        assertThat(quiz.titles).hasSize(4)
        assertThat(quiz.artists.map { normalizeString(it) }).contains(normalizeString(current.artist))
        assertThat(quiz.titles.map { normalizeString(it) }).contains(normalizeString(current.title))
    }
}

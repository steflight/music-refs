package ca.kladriva.musicrefs.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp

val NeonPink = Color(0xFFFF007F)
val NeonCyan = Color(0xFF00F0FF)
val BgDark = Color(0xFF0B0F19)
val SurfaceDark = Color(0xFF121826)
val OnDark = Color(0xFFF5F7FF)
val Muted = Color(0xFF9AA3B5)

private val ColorScheme = darkColorScheme(
    primary = NeonPink,
    secondary = NeonCyan,
    background = BgDark,
    surface = SurfaceDark,
    onPrimary = Color.White,
    onSecondary = BgDark,
    onBackground = OnDark,
    onSurface = OnDark,
    error = Color(0xFFFF6B6B),
)

private val DisplayFamily = FontFamily.SansSerif
private val BodyFamily = FontFamily.SansSerif

val BrandDisplay = TextStyle(
    fontFamily = DisplayFamily,
    fontWeight = FontWeight.Black,
    fontSize = 36.sp,
    letterSpacing = 4.sp,
    color = OnDark,
)

val SectionTitle = TextStyle(
    fontFamily = DisplayFamily,
    fontWeight = FontWeight.Bold,
    fontSize = 22.sp,
    letterSpacing = 1.sp,
    color = OnDark,
)

val BodyReadable = TextStyle(
    fontFamily = BodyFamily,
    fontWeight = FontWeight.Normal,
    fontSize = 16.sp,
    lineHeight = 22.sp,
    color = OnDark,
)

val QuoteStyle = TextStyle(
    fontFamily = BodyFamily,
    fontWeight = FontWeight.SemiBold,
    fontSize = 20.sp,
    lineHeight = 28.sp,
    textAlign = TextAlign.Center,
    color = OnDark,
)

@Composable
fun MusicRefsTheme(content: @Composable () -> Unit) {
    @Suppress("UNUSED_VARIABLE")
    val dark = isSystemInDarkTheme()
    MaterialTheme(
        colorScheme = ColorScheme,
        typography = MaterialTheme.typography.copy(
            displayLarge = BrandDisplay,
            titleLarge = SectionTitle,
            bodyLarge = BodyReadable,
        ),
        content = content,
    )
}
